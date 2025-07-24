#!/usr/bin/env python3
"""
Simple script to edit Q&A bot configuration
"""

import json
import os
from src.config_loader import load_qa_config, save_qa_config

def edit_config():
    """Interactive configuration editor"""
    print("🔧 Q&A Bot Configuration Editor")
    print("=" * 40)
    
    # Load current config
    config = load_qa_config()
    
    while True:
        print("\n📊 Current Configuration:")
        print("1. Context Settings:")
        print(f"   - Documents retrieved: {config['context_settings']['default_top_k']}")
        print(f"   - Context length (tokens): {config['context_settings']['default_context_length']}")
        print(f"   - Max context chars: {config['context_settings']['max_context_chars']}")
        
        print("\n2. Model Settings:")
        print(f"   - LLM Model: {config['model_settings']['llm_model']}")
        print(f"   - Embedding Model: {config['model_settings']['embedding_model']}")
        
        print("\n3. Debug Settings:")
        print(f"   - Debug logging: {config['debug_settings']['enable_debug_logging']}")
        
        print("\nOptions:")
        print("1 - Change documents retrieved")
        print("2 - Change context length")
        print("3 - Change max context chars")
        print("4 - Toggle debug logging")
        print("5 - Save and exit")
        print("6 - Exit without saving")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            try:
                new_value = int(input(f"Enter new number of documents (current: {config['context_settings']['default_top_k']}): "))
                config['context_settings']['default_top_k'] = new_value
                print(f"✅ Set documents retrieved to {new_value}")
            except ValueError:
                print("❌ Please enter a valid number")
                
        elif choice == '2':
            try:
                new_value = int(input(f"Enter new context length (current: {config['context_settings']['default_context_length']}): "))
                config['context_settings']['default_context_length'] = new_value
                print(f"✅ Set context length to {new_value}")
            except ValueError:
                print("❌ Please enter a valid number")
                
        elif choice == '3':
            try:
                new_value = int(input(f"Enter new max context chars (current: {config['context_settings']['max_context_chars']}): "))
                config['context_settings']['max_context_chars'] = new_value
                print(f"✅ Set max context chars to {new_value}")
            except ValueError:
                print("❌ Please enter a valid number")
                
        elif choice == '4':
            current = config['debug_settings']['enable_debug_logging']
            config['debug_settings']['enable_debug_logging'] = not current
            print(f"✅ Toggled debug logging to {not current}")
            
        elif choice == '5':
            if save_qa_config(config):
                print("✅ Configuration saved successfully!")
            break
            
        elif choice == '6':
            print("❌ Exiting without saving changes")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1-6.")

if __name__ == "__main__":
    edit_config() 