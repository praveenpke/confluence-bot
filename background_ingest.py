#!/usr/bin/env python3
"""
Background Ingestion System
Allows real-time querying while ingestion runs in background
"""

import os
import sys
import time
import threading
import signal
from datetime import datetime
from src.ingest import ingest_from_config
from src.vector_store import get_collection_stats, collection_exists, create_collection

class BackgroundIngestion:
    def __init__(self):
        self.ingestion_running = False
        self.ingestion_thread = None
        self.stop_requested = False
        
    def start_background_ingestion(self, incremental=True, daily=False, force=False):
        """
        Start ingestion in background thread
        """
        if self.ingestion_running:
            print("⚠️ Ingestion already running")
            return
        
        self.ingestion_running = True
        self.stop_requested = False
        
        # Start ingestion in background thread
        self.ingestion_thread = threading.Thread(
            target=self._run_ingestion,
            args=(incremental, daily, force),
            daemon=True
        )
        self.ingestion_thread.start()
        
        print("🚀 Background ingestion started")
        print("💡 You can now query the system while ingestion runs")
        
    def _run_ingestion(self, incremental, daily, force):
        """
        Run ingestion in background thread
        """
        try:
            print(f"🔄 Starting background ingestion...")
            print(f"   Mode: {'Incremental' if incremental else 'Daily' if daily else 'Full'}")
            
            # Ensure collection exists
            if not collection_exists():
                create_collection()
            
            # Run ingestion
            ingest_from_config(incremental=incremental, daily=daily, force=force)
            
            print("✅ Background ingestion completed")
            
        except Exception as e:
            print(f"❌ Background ingestion error: {e}")
        finally:
            self.ingestion_running = False
    
    def stop_ingestion(self):
        """
        Stop background ingestion
        """
        if not self.ingestion_running:
            print("⚠️ No ingestion running")
            return
        
        self.stop_requested = True
        print("🛑 Stopping background ingestion...")
        
        # Wait for thread to finish
        if self.ingestion_thread:
            self.ingestion_thread.join(timeout=30)
        
        self.ingestion_running = False
        print("✅ Background ingestion stopped")
    
    def get_status(self):
        """
        Get ingestion status
        """
        stats = get_collection_stats()
        
        status = {
            "ingestion_running": self.ingestion_running,
            "stop_requested": self.stop_requested,
            "collection_stats": stats
        }
        
        return status
    
    def print_status(self):
        """
        Print current status
        """
        status = self.get_status()
        
        print("📊 Background Ingestion Status:")
        print(f"   Running: {'✅ Yes' if status['ingestion_running'] else '❌ No'}")
        print(f"   Stop Requested: {'✅ Yes' if status['stop_requested'] else '❌ No'}")
        
        if status['collection_stats']:
            stats = status['collection_stats']
            print(f"   Collection Points: {stats.get('points_count', 0)}")
            print(f"   Collection Status: {stats.get('status', 'unknown')}")
            print(f"   Indexed Vectors: {stats.get('indexed_vectors_count', 0)}")
        else:
            print("   Collection: Not available")

def main():
    """
    Main function for background ingestion
    """
    if len(sys.argv) < 2:
        print("""
🚀 Background Ingestion System

Usage:
  python background_ingest.py [command] [options]

Commands:
  start     - Start background ingestion
  stop      - Stop background ingestion
  status    - Show status
  query     - Test query while ingestion runs

Options for start:
  --incremental - Run incremental ingestion (default)
  --daily       - Run daily ingestion
  --force       - Force full ingestion

Examples:
  python background_ingest.py start
  python background_ingest.py start --incremental
  python background_ingest.py start --force
  python background_ingest.py status
  python background_ingest.py stop
  python background_ingest.py query
""")
        return
    
    command = sys.argv[1].lower()
    bg_ingest = BackgroundIngestion()
    
    if command == "start":
        # Parse options
        incremental = "--incremental" in sys.argv or "--daily" not in sys.argv and "--force" not in sys.argv
        daily = "--daily" in sys.argv
        force = "--force" in sys.argv
        
        bg_ingest.start_background_ingestion(incremental=incremental, daily=daily, force=force)
        
        # Keep main thread alive
        try:
            while bg_ingest.ingestion_running and not bg_ingest.stop_requested:
                time.sleep(5)
                print("💡 Ingestion running... Press Ctrl+C to stop")
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal")
            bg_ingest.stop_ingestion()
    
    elif command == "stop":
        bg_ingest.stop_ingestion()
    
    elif command == "status":
        bg_ingest.print_status()
    
    elif command == "query":
        # Test query functionality
        print("🧪 Testing query functionality...")
        from src.query import main as query_main
        query_main()
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main() 