#!/usr/bin/env python3
"""
Demo script to show incremental ingestion capabilities
"""

import os
import sys
from src.ingest import ingest_from_config

def demo_incremental_ingestion():
    """
    Demonstrate the new incremental ingestion features
    """
    print("🚀 Demo: Incremental Ingestion System")
    print("=" * 50)
    
    # Show current status
    print("\n1. 📊 Current Status:")
    from src.ingest import load_progress
    progress = load_progress()
    print(f"   - Last run: {progress.get('last_run', 'Never')}")
    print(f"   - Total documents: {progress.get('total_documents', 0)}")
    print(f"   - Spaces processed: {len(progress.get('processed_spaces', {}))}")
    
    # Demo different modes
    print("\n2. 🔄 Available Modes:")
    print("   - Full ingestion: python main.py ingest-config --force")
    print("   - Incremental: python main.py ingest-config --incremental")
    print("   - Daily: python main.py ingest-config --daily")
    print("   - Status check: python main.py ingest-config --status")
    
    print("\n3. 💡 Key Features:")
    print("   ✅ Progress tracking - knows what's been processed")
    print("   ✅ Change detection - only processes new/updated content")
    print("   ✅ Resume capability - continues from where it left off")
    print("   ✅ Daily automation - can be scheduled with cron")
    print("   ✅ Detailed logging - tracks what was updated vs skipped")
    
    print("\n4. 📁 Files Created:")
    print("   - progress/ingestion_progress.json - tracks all progress")
    print("   - logs/ - contains detailed ingestion logs")
    
    print("\n5. 🎯 Usage Examples:")
    print("   # First time (full ingestion)")
    print("   python main.py ingest-config --force")
    print()
    print("   # Daily incremental update")
    print("   python main.py ingest-config --daily")
    print()
    print("   # Manual incremental update")
    print("   python main.py ingest-config --incremental")
    print()
    print("   # Check status")
    print("   python main.py ingest-config --status")

if __name__ == "__main__":
    demo_incremental_ingestion()
