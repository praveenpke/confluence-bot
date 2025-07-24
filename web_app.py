#!/usr/bin/env python3
"""
Flask web application for Confluence Q&A Bot
"""

import os
import json
import time
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from src.ollama_client import get_embedding
from src.vector_store import query_similar, get_answer, get_context_config
from src.config_loader import load_qa_config
from src.format_response import enhance_response_formatting

app = Flask(__name__)
CORS(app)

# Load configuration
config = load_qa_config()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        data = request.get_json()
        query = data.get('message', '').strip()
        
        if not query:
            return jsonify({'error': 'No message provided'}), 400
        
        # Get embedding for the query
        vector = get_embedding(query)
        if not vector:
            return jsonify({'error': 'Failed to generate embedding'}), 500
        
        # Get similar documents
        context_docs = query_similar(vector)
        
        if not context_docs:
            return jsonify({'error': 'No relevant documents found'}), 404
        
        # Prepare sources for response
        sources = []
        for i, doc in enumerate(context_docs, 1):
            title = (doc.payload.get("page_title") or 
                    doc.payload.get("title") or 
                    doc.payload.get("attachment_title") or 
                    "Unknown")
            
            url = doc.payload.get("url", "")
            content_type = doc.payload.get("content_type", "page")
            space_name = doc.payload.get("space_name", "")
            
            source_info = {
                "id": i,
                "title": title,
                "url": url,
                "content_type": content_type,
                "space_name": space_name
            }
            sources.append(source_info)
        
        # Generate answer
        answer = get_answer(query, context_docs)
        
        # Enhance formatting
        formatted_answer = enhance_response_formatting(answer)
        
        return jsonify({
            'answer': formatted_answer,
            'sources': sources,
            'query': query
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

@app.route('/api/stream-chat', methods=['POST'])
def stream_chat():
    """Handle streaming chat requests"""
    try:
        data = request.get_json()
        query = data.get('message', '').strip()
        
        if not query:
            return jsonify({'error': 'No message provided'}), 400
        
        def generate():
            # Send initial response
            yield f"data: {json.dumps({'type': 'start', 'query': query})}\n\n"
            
            # Get embedding for the query
            vector = get_embedding(query)
            if not vector:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to generate embedding'})}\n\n"
                return
            
            # Get similar documents
            context_docs = query_similar(vector)
            
            if not context_docs:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No relevant documents found'})}\n\n"
                return
            
            # Send sources info
            sources = []
            for i, doc in enumerate(context_docs, 1):
                title = (doc.payload.get("page_title") or 
                        doc.payload.get("title") or 
                        doc.payload.get("attachment_title") or 
                        "Unknown")
                
                url = doc.payload.get("url", "")
                content_type = doc.payload.get("content_type", "page")
                space_name = doc.payload.get("space_name", "")
                
                source_info = {
                    "id": i,
                    "title": title,
                    "url": url,
                    "content_type": content_type,
                    "space_name": space_name
                }
                sources.append(source_info)
            
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            
            # Generate answer
            answer = get_answer(query, context_docs)
            
            # Enhance formatting
            formatted_answer = enhance_response_formatting(answer)
            
            # Stream the answer character by character
            for char in formatted_answer:
                yield f"data: {json.dumps({'type': 'char', 'char': char})}\n\n"
                time.sleep(0.01)  # Small delay for typing effect
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
        
        return Response(generate(), mimetype='text/plain')
        
    except Exception as e:
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        context_config = get_context_config()
        return jsonify({
            'context_settings': context_config,
            'qa_config': config
        })
    except Exception as e:
        return jsonify({'error': f'Error getting config: {str(e)}'}), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        data = request.get_json()
        
        # Update context settings
        if 'context_settings' in data:
            from src.vector_store import set_context_config
            context_settings = data['context_settings']
            
            set_context_config(
                top_k=context_settings.get('top_k'),
                context_length=context_settings.get('context_length'),
                max_context_chars=context_settings.get('max_context_chars')
            )
        
        return jsonify({'message': 'Configuration updated successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Error updating config: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 