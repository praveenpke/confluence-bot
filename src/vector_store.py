# src/vector_store.py

import os
import textwrap
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from src.ollama_client import call_model
from src.config_loader import load_qa_config

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "confluence_docs"

# Load configuration
config = load_qa_config()

# Context size configuration from config file
DEFAULT_TOP_K = config["context_settings"]["default_top_k"]
DEFAULT_CONTEXT_LENGTH = config["context_settings"]["default_context_length"]
MAX_CONTEXT_CHARS = config["context_settings"]["max_context_chars"]

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def create_collection():
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )


def upsert_embeddings(docs):
    """
    Upsert embeddings into the vector database with unique IDs
    """
    points = []
    
    # Get the next available ID
    try:
        # Get current collection info to find next ID
        collection_info = client.get_collection(COLLECTION_NAME)
        current_count = collection_info.points_count or 0
        next_id = current_count
    except:
        next_id = 0
    
    for i, doc in enumerate(docs):
        payload = {"text": doc["text"]}
        # Add metadata if available
        if "metadata" in doc:
            payload.update(doc["metadata"])
        
        # Use unique ID for each document
        unique_id = next_id + i
        
        points.append(PointStruct(id=unique_id, vector=doc["vector"], payload=payload))
    
    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"        ✅ Upserted {len(points)} documents with IDs {next_id} to {next_id + len(points) - 1}")


def query_similar(vector, top_k=DEFAULT_TOP_K):
    """
    Query similar documents with configurable context size.
    
    Args:
        vector: The query vector
        top_k: Number of documents to retrieve (default from config)
    """
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        limit=top_k
    )
    return results  # Return full results so get_answer can extract from payload


def get_answer(query: str, docs: list) -> str:
    """
    Generate an answer using the retrieved documents and the query.
    """
    if not docs:
        return "No relevant documents found."

    # Extract context from documents
    context_parts = []
    print(f"\n🔍 DEBUG: Processing {len(docs)} documents...")
    
    for i, doc in enumerate(docs, 1):
        print(f"  Document {i}:")
        print(f"    Payload keys: {list(doc.payload.keys()) if hasattr(doc, 'payload') else 'No payload'}")
        
        if hasattr(doc, 'payload') and doc.payload:
            # Try different possible text fields
            text = None
            if 'text' in doc.payload:
                text = doc.payload['text']
                print(f"    Found 'text' field with {len(text)} characters")
            elif 'content' in doc.payload:
                text = doc.payload['content']
                print(f"    Found 'content' field with {len(text)} characters")
            else:
                print(f"    No text field found in payload")
            
            if text:
                # Additional cleaning for any remaining HTML or formatting issues
                import re
                text = re.sub(r'<[^>]+>', '', text)
                # Clean up extra whitespace
                text = ' '.join(text.split())
                if text.strip():
                    title = doc.payload.get("page_title", doc.payload.get("title", f"Document {i}"))
                    context_parts.append(f"Document {i} ({title}):\n{text}")
                    print(f"    ✅ Added to context: {title}")
                else:
                    print(f"    ❌ Text is empty after cleaning")
            else:
                print(f"    ❌ No text content found")
        else:
            print(f"    ❌ No payload found")

    context = "\n\n---\n\n".join(context_parts)

    # Limit context size to prevent token overflow
    if len(context) > MAX_CONTEXT_CHARS:
        print(f"⚠️ Context too large ({len(context)} chars), truncating to {MAX_CONTEXT_CHARS} chars")
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated due to size limits...]"

    # Get prompt settings from config
    system_prompt = config["prompt_settings"]["system_prompt"]
    instruction = config["prompt_settings"]["instruction"]
    
    prompt = textwrap.dedent(f"""
        {system_prompt}
        
        {instruction}
        
        Context from Confluence documents and PDFs:
        {context}
        
        Question: {query}
        
        Answer (be specific and reference the documents):
    """)

    # Debug logging based on config
    if config["debug_settings"]["enable_debug_logging"]:
        print(f"\n🔍 DEBUG: Prompt being sent to LLM:")
        print(f"Context length: {len(context)} characters")
        
        if config["debug_settings"]["show_context_preview"]:
            print(f"Context preview: {context[:500]}...")
        
        print(f"Question: {query}")
        print(f"---")

    # Use configurable context length for better responses
    return call_model(prompt, context_length=DEFAULT_CONTEXT_LENGTH)


def set_context_config(top_k=None, context_length=None, max_context_chars=None):
    """
    Dynamically adjust context configuration and save to config file.
    
    Args:
        top_k: Number of documents to retrieve
        context_length: Token limit for LLM context
        max_context_chars: Maximum characters in context
    """
    global DEFAULT_TOP_K, DEFAULT_CONTEXT_LENGTH, MAX_CONTEXT_CHARS
    from src.config_loader import update_config_section
    
    if top_k is not None:
        DEFAULT_TOP_K = top_k
        update_config_section("context_settings", "default_top_k", top_k)
        print(f"✅ Set top_k to {DEFAULT_TOP_K}")
    
    if context_length is not None:
        DEFAULT_CONTEXT_LENGTH = context_length
        update_config_section("context_settings", "default_context_length", context_length)
        print(f"✅ Set context_length to {DEFAULT_CONTEXT_LENGTH}")
    
    if max_context_chars is not None:
        MAX_CONTEXT_CHARS = max_context_chars
        update_config_section("context_settings", "max_context_chars", max_context_chars)
        print(f"✅ Set max_context_chars to {MAX_CONTEXT_CHARS}")


def get_context_config():
    """
    Get current context configuration.
    """
    return {
        "top_k": DEFAULT_TOP_K,
        "context_length": DEFAULT_CONTEXT_LENGTH,
        "max_context_chars": MAX_CONTEXT_CHARS
    }
