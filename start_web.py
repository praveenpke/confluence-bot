#!/usr/bin/env python3
"""
Simple startup script for the web interface
"""

import webbrowser
import time
import threading
from web_app import app

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)
    webbrowser.open('http://localhost:5001')

if __name__ == '__main__':
    print("🌐 Starting ELP Crew Rules Q&A Bot Web Interface...")
    print("📱 Opening browser to http://localhost:5001")
    print("🛑 Press Ctrl+C to stop the server\n")
    
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Flask app
    app.run(debug=False, host='0.0.0.0', port=5001) 