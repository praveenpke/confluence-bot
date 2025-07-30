# src/query.py

import os
from src.ollama_client import get_embedding, call_model
from src.vector_store import search_similar, get_collection_stats, collection_exists
from src.config_loader import load_qa_config

# Load configuration
config = load_qa_config()
DEFAULT_TOP_K = config["search_settings"]["top_k"]
MAX_CONTEXT_CHARS = config["context_settings"]["max_context_chars"]

def get_answer(query, top_k=DEFAULT_TOP_K):
    """
    Get answer for a query with graceful fallback when no data is available
    """
    try:
        # Check if collection exists and has data
        if not collection_exists():
            return {
                "answer": "I don't have any knowledge base set up yet. Please run ingestion first.",
                "sources": [],
                "confidence": "low",
                "status": "no_collection"
            }
        
        # Get collection stats
        stats = get_collection_stats()
        if not stats or stats.get('points_count', 0) == 0:
            return {
                "answer": "I don't have any documents loaded yet. The ingestion process may still be running. Please try again in a few minutes.",
                "sources": [],
                "confidence": "low",
                "status": "no_data"
            }
        
        # Get query embedding
        query_vector = get_embedding(query)
        if not query_vector:
            return {
                "answer": "Sorry, I couldn't process your query. Please try again.",
                "sources": [],
                "confidence": "low",
                "status": "embedding_error"
            }
        
        # Search for similar documents
        results = search_similar(query_vector, limit=top_k)
        
        if not results:
            return {
                "answer": "I couldn't find any relevant information for your query. The ingestion process may still be running, or your question might be outside the scope of my knowledge base.",
                "sources": [],
                "confidence": "low",
                "status": "no_matches"
            }
        
        # Build context from results
        context = ""
        sources = []
        
        for result in results:
            text = result.payload.get("text", "")
            metadata = {k: v for k, v in result.payload.items() if k != "text"}
            
            # Add to context if we haven't exceeded the limit
            if len(context) + len(text) < MAX_CONTEXT_CHARS:
                context += text + "\n\n"
                sources.append({
                    "text": text[:200] + "..." if len(text) > 200 else text,
                    "metadata": metadata,
                    "score": result.score
                })
        
        # Generate answer using LLM
        prompt = f"""Based on the following context, answer the user's question. If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {query}

Answer:"""

        answer = call_model(prompt)
        
        # Determine confidence based on results
        if results and results[0].score > 0.7:
            confidence = "high"
        elif results and results[0].score > 0.5:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "status": "success",
            "total_documents": stats.get('points_count', 0)
        }
        
    except Exception as e:
        return {
            "answer": f"Sorry, I encountered an error: {str(e)}",
            "sources": [],
            "confidence": "low",
            "status": "error"
        }

def main():
    """
    Interactive Q&A session
    """
    print("🤖 Confluence Q&A Bot")
    print("Type 'exit' to quit\n")
    
    # Check initial status
    stats = get_collection_stats()
    if stats:
        print(f"📊 Knowledge base: {stats.get('points_count', 0)} documents loaded")
    else:
        print("📊 Knowledge base: Not available")
    
    print("\n💡 You can ask questions even while ingestion is running!")
    print("   The system will use whatever data is available.\n")
    
    while True:
        try:
            query = input("❓ Your question: ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            print("\n🔍 Searching...")
            result = get_answer(query)
            
            # Print answer
            print(f"\n💬 Answer: {result['answer']}")
            
            # Print status info
            if result['status'] == 'success':
                print(f"📊 Confidence: {result['confidence']}")
                if result['sources']:
                    print(f"📚 Sources: {len(result['sources'])} documents")
                    for i, source in enumerate(result['sources'][:2], 1):
                        print(f"   {i}. {source['text'][:100]}...")
            else:
                print(f"⚠️ Status: {result['status']}")
            
            print("\n" + "="*50 + "\n")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
