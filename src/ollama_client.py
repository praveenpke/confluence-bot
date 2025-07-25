# src/ollama_client.py

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Ollama URL from environment variable, fallback to localhost
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama2"

def get_embedding(text: str):
    """
    Get embedding vector for the given text using Ollama.
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text}
        )
        response.raise_for_status()
        data = response.json()
        embedding = data.get("embedding", [])
        if not embedding:
            print("⚠️ Warning: Empty embedding returned.")
        return embedding
    except Exception as e:
        print(f"❌ Failed to get embedding: {e}")
        return []

def call_model(prompt: str, context_length=8192):
    """
    Get a response from a language model using Ollama.
    
    Args:
        prompt: The prompt to send to the model
        context_length: Maximum context length (default: 8192 tokens)
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": LLM_MODEL, 
                "prompt": prompt, 
                "stream": False,
                "options": {
                    "num_ctx": context_length  # Increase context window
                }
            }
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"❌ Error calling model: {e}")
        return "Error calling language model."
