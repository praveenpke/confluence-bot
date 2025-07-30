#!/usr/bin/env python3
"""
Confluence Q&A Bot - Main Orchestrator

This script provides a simple interface to interact with the Confluence Q&A system.
"""

import sys
import os
import argparse
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
  web           - Start web-based chat interface
  config        - Edit Q&A bot configuration
  help          - Show this help message

Options for ingest commands:
  --incremental - Run in incremental mode (skip unchanged documents)
  --daily       - Run in daily mode (only if last run was >24h ago)
  --force       - Force full ingestion even in incremental/daily mode
  --no-resume   - Don't resume from previous progress (start fresh)
  --status      - Show ingestion status and progress
  --progress    - Show detailed progress information

Examples:
  python main.py test
  python main.py ingest
  python main.py ingest SPACE_KEY
  python main.py ingest-config
  python main.py ingest-config --incremental
  python main.py ingest-config --daily
  python main.py ingest-config --force
  python main.py ingest-config --no-resume
  python main.py ingest-local
  python main.py query
  python main.py web
  python main.py config

Environment Variables:
  CONFLUENCE_BASE_URL    - Your Confluence instance URL
  CONFLUENCE_USERNAME    - Your Confluence username
  CONFLUENCE_API_TOKEN   - Your Confluence API token
  QDRANT_HOST           - Qdrant host (default: localhost)
  QDRANT_PORT           - Qdrant port (default: 6333)
""")

def show_ingestion_status():
    """
    Show current ingestion status and progress
    """
    import json
    import os
    from datetime import datetime
    
    progress_path = os.path.join("progress", "ingestion_progress.json")
    
    if os.path.exists(progress_path):
        try:
            with open(progress_path, "r") as f:
                progress = json.load(f)
            
            print("📊 Ingestion Status:")
            print(f"  Last run: {progress.get('last_run', 'Never')}")
            print(f"  Total documents: {progress.get('total_documents', 0)}")
            print(f"  Spaces processed: {len(progress.get('processed_spaces', {}))}")
            print(f"  Pages processed: {len(progress.get('processed_pages', {}))}")
            
            # Show current progress
            current_progress = progress.get('current_progress', {})
            if current_progress:
                percentage = current_progress.get('percentage_complete', 0.0)
                current_space = current_progress.get('current_space_index', 0)
                total_spaces = current_progress.get('total_spaces', 0)
                current_page = current_progress.get('current_page_index', 0)
                total_pages = current_progress.get('total_pages', 0)
                
                print(f"\n🔄 Current Progress:")
                print(f"  Progress: {percentage:.1f}% Complete")
                print(f"  Space: {current_space + 1}/{total_spaces}")
                print(f"  Page: {current_page + 1}/{total_pages}")
                
                if percentage > 0 and percentage < 100:
                    print(f"  ⚠️  Incomplete - can resume from {percentage:.1f}%")
            
            if progress.get('last_updated'):
                print(f"  Last updated: {progress.get('last_updated')}")
            
            print("\n📋 Processed Spaces:")
            for space_key, space_info in progress.get('processed_spaces', {}).items():
                print(f"  - {space_key}: {space_info.get('page_count', 0)} pages")
                
        except Exception as e:
            print(f"❌ Error reading progress: {e}")
    else:
        print("📊 No ingestion progress found (first run)")

def show_detailed_progress():
    """
    Show detailed progress information with recent pages
    """
    import json
    import os
    
    progress_path = os.path.join("progress", "ingestion_progress.json")
    
    if os.path.exists(progress_path):
        try:
            with open(progress_path, "r") as f:
                progress = json.load(f)
            
            # Show basic status
            show_ingestion_status()
            
            # Show recent pages
            print("\n📄 Recent Pages Processed:")
            pages = progress.get('processed_pages', {})
            recent_pages = list(pages.items())[-20:]  # Show last 20
            
            for page_id, page_info in recent_pages:
                metadata = page_info.get('metadata', {})
                page_title = metadata.get('page_title', 'Unknown')
                space_name = metadata.get('space_name', 'Unknown')
                last_processed = page_info.get('last_processed', 'Unknown')
                
                print(f"  - {page_title} ({space_name}) - {last_processed}")
            
            # Show space details
            print("\n🌐 Space Details:")
            for space_key, space_info in progress.get('processed_spaces', {}).items():
                page_count = space_info.get('page_count', 0)
                last_processed = space_info.get('last_processed', 'Unknown')
                print(f"  - {space_key}: {page_count} pages (last: {last_processed})")
                
        except Exception as e:
            print(f"❌ Error reading detailed progress: {e}")
    else:
        print("📊 No ingestion progress found (first run)")

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
        # Parse arguments for ingest command
        parser = argparse.ArgumentParser(description="Ingest documents from Confluence")
        parser.add_argument("space_key", nargs="?", help="Space key to ingest (optional)")
        parser.add_argument("--incremental", action="store_true", help="Run in incremental mode")
        parser.add_argument("--daily", action="store_true", help="Run in daily mode")
        parser.add_argument("--force", action="store_true", help="Force full ingestion")
        parser.add_argument("--no-resume", action="store_true", help="Don't resume from previous progress")
        
        # Parse only the arguments after "ingest"
        args = parser.parse_args(sys.argv[2:])
        
        space_key = args.space_key
        print("📚 Starting Confluence ingestion...")
        if space_key:
            print(f"📂 Using space key: {space_key}")
        ingest_from_confluence(space_key)
    
    elif command == "ingest-config":
        # Parse arguments for ingest-config command
        parser = argparse.ArgumentParser(description="Ingest documents from configured spaces")
        parser.add_argument("--incremental", action="store_true", help="Run in incremental mode (skip unchanged documents)")
        parser.add_argument("--daily", action="store_true", help="Run in daily mode (only if last run was >24h ago)")
        parser.add_argument("--force", action="store_true", help="Force full ingestion even in incremental/daily mode")
        parser.add_argument("--no-resume", action="store_true", help="Don't resume from previous progress (start fresh)")
        parser.add_argument("--status", action="store_true", help="Show ingestion status")
        parser.add_argument("--progress", action="store_true", help="Show detailed progress")
        
        # Parse only the arguments after "ingest-config"
        args = parser.parse_args(sys.argv[2:])
        
        if args.status:
            show_ingestion_status()
            return
        
        if args.progress:
            show_detailed_progress()
            return
        
        print("📋 Starting ingestion from configured spaces...")
        
        # Determine mode
        if args.incremental:
            mode = "Incremental"
        elif args.daily:
            mode = "Daily"
        else:
            mode = "Full"
        
        if args.no_resume:
            mode += " (Fresh Start)"
        else:
            mode += " (Resume Enabled)"
        
        print(f"Mode: {mode}")
        ingest_from_config(incremental=args.incremental, daily=args.daily, force=args.force, resume=not args.no_resume)
    
    elif command == "ingest-local":
        print("📁 Starting local document ingestion...")
        ingest_from_local_docs()
    
    elif command == "query":
        print("🤖 Starting interactive Q&A session...")
        print("Type 'exit' to quit\n")
        query_main()
    
    elif command == "web":
        print("🌐 Starting web-based chat interface...")
        print("Opening browser to http://localhost:5001")
        print("Press Ctrl+C to stop the server\n")
        from web_app import app
        app.run(debug=False, host='0.0.0.0', port=5001)
    
    elif command == "config":
        print("🔧 Starting configuration editor...")
        from edit_config import edit_config
        edit_config()
    
    elif command == "status":
        show_ingestion_status()
    
    elif command == "progress":
        show_detailed_progress()
    
    else:
        print(f"❌ Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main() 