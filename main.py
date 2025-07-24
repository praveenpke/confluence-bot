#!/usr/bin/env python3
"""
Confluence Q&A Bot - Main Orchestrator

This script provides a simple interface to interact with the Confluence Q&A system.
"""

import sys
import os
from src.confluence_client import test_confluence_connection
from src.ingest import ingest_from_confluence, ingest_from_local_docs, ingest_from_config
from src.query import main as query_main

def show_help():
    print("""
🤖 Confluence Q&A Bot

Usage:
  python main.py [command] [options]

Commands:
  test          - Test Confluence connection
  ingest        - Ingest documents from Confluence
  ingest-config - Ingest documents from configured spaces (with nested spaces)
  ingest-local  - Ingest documents from local docs folder
  query         - Start interactive Q&A session
  config        - Edit Q&A bot configuration
  help          - Show this help message

Examples:
  python main.py test
  python main.py ingest
  python main.py ingest SPACE_KEY
  python main.py ingest-config
  python main.py ingest-local
  python main.py query
  python main.py config

Environment Variables:
  CONFLUENCE_BASE_URL    - Your Confluence instance URL
  CONFLUENCE_USERNAME    - Your Confluence username
  CONFLUENCE_API_TOKEN   - Your Confluence API token
  QDRANT_HOST           - Qdrant host (default: localhost)
  QDRANT_PORT           - Qdrant port (default: 6333)
""")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "help":
        show_help()
    
    elif command == "test":
        print("🔗 Testing Confluence connection...")
        test_confluence_connection()
    
    elif command == "ingest":
        space_key = sys.argv[2] if len(sys.argv) > 2 else None
        print("📚 Starting Confluence ingestion...")
        ingest_from_confluence(space_key)
    
    elif command == "ingest-config":
        print("📋 Starting ingestion from configured spaces...")
        ingest_from_config()
    
    elif command == "ingest-local":
        print("📁 Starting local document ingestion...")
        ingest_from_local_docs()
    
    elif command == "query":
        print("🤖 Starting interactive Q&A session...")
        print("Type 'exit' to quit\n")
        query_main()
    
    elif command == "config":
        print("🔧 Starting configuration editor...")
        from edit_config import edit_config
        edit_config()
    
    else:
        print(f"❌ Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main() 