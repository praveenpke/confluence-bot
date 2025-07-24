# src/config_loader.py

import json
import os
from typing import Dict, Any

DEFAULT_CONFIG_PATH = "config/qa_config.json"

def load_qa_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """
    Load Q&A bot configuration from JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing configuration settings
    """
    try:
        if not os.path.exists(config_path):
            print(f"⚠️ Configuration file not found at {config_path}, using defaults")
            return get_default_config()
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"✅ Loaded configuration from {config_path}")
        return config
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        print("Using default configuration")
        return get_default_config()

def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration settings.
    """
    return {
        "context_settings": {
            "default_top_k": 10,
            "default_context_length": 16384,
            "max_context_chars": 50000,
            "description": "Number of documents to retrieve for context"
        },
        "model_settings": {
            "llm_model": "llama2",
            "embedding_model": "nomic-embed-text",
            "ollama_url": "http://localhost:11434"
        },
        "prompt_settings": {
            "system_prompt": "You are an AI assistant for the ELP Aviation Crew Rules software system. This system manages crew rules and regulations for airlines.",
            "instruction": "Answer the question based ONLY on the provided context. If the context contains the information, provide a detailed, specific answer. If the context doesn't contain enough information, say 'I don't have enough information in the provided documents to answer this question.' Do NOT make up information or provide generic answers. Be specific and reference the actual content from the documents."
        },
        "debug_settings": {
            "enable_debug_logging": True,
            "show_context_preview": True,
            "show_document_details": True
        }
    }

def save_qa_config(config: Dict[str, Any], config_path: str = DEFAULT_CONFIG_PATH) -> bool:
    """
    Save Q&A bot configuration to JSON file.
    
    Args:
        config: Configuration dictionary to save
        config_path: Path to save the configuration file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration saved to {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False

def update_config_section(section: str, key: str, value: Any, config_path: str = DEFAULT_CONFIG_PATH) -> bool:
    """
    Update a specific configuration value.
    
    Args:
        section: Configuration section (e.g., 'context_settings')
        key: Configuration key within the section
        value: New value to set
        config_path: Path to the configuration file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        config = load_qa_config(config_path)
        
        if section not in config:
            config[section] = {}
        
        config[section][key] = value
        
        return save_qa_config(config, config_path)
        
    except Exception as e:
        print(f"❌ Error updating configuration: {e}")
        return False

def get_config_value(section: str, key: str, config_path: str = DEFAULT_CONFIG_PATH) -> Any:
    """
    Get a specific configuration value.
    
    Args:
        section: Configuration section
        key: Configuration key within the section
        config_path: Path to the configuration file
        
    Returns:
        Configuration value or None if not found
    """
    try:
        config = load_qa_config(config_path)
        return config.get(section, {}).get(key)
    except Exception as e:
        print(f"❌ Error getting configuration value: {e}")
        return None 