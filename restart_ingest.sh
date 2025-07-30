#!/bin/bash

# Robust Ingestion Script for Confluence Bot
# This script handles ingestion with proper error handling and logging

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Configuration
PROJECT_DIR="/mnt/data/confluence-bot"
VENV_DIR="/mnt/data/venv"
LOG_DIR="/mnt/data/logs"
PID_FILE="/tmp/ingest.pid"
MAX_RETRIES=3
RETRY_DELAY=60

# Create log directory
mkdir -p "$LOG_DIR"

# Function to check if process is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to kill existing process
kill_existing() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        log "Killing existing ingestion process (PID: $pid)"
        kill "$pid" 2>/dev/null || true
        sleep 5
        rm -f "$PID_FILE"
    fi
}

# Function to test Ollama connection
test_ollama() {
    log "Testing Ollama connection..."
    local response=$(curl -s -X POST https://4bbqnd60agv3z6-5123.proxy.runpod.net/api/embeddings \
        -H "Content-Type: application/json" \
        -d '{"model": "nomic-embed-text", "prompt": "Test"}' 2>/dev/null)
    
    if echo "$response" | grep -q "embedding"; then
        success "Ollama connection successful"
        return 0
    else
        error "Ollama connection failed"
        return 1
    fi
}

# Function to delete and recreate Qdrant collection
reset_collection() {
    log "Resetting Qdrant collection..."
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    python -c "
from src.vector_store import client
try:
    client.delete_collection('confluence_docs')
    print('Collection deleted successfully')
except Exception as e:
    print(f'Error deleting collection: {e}')
" 2>&1 | tee -a "$LOG_DIR/collection_reset.log"
    
    success "Collection reset completed"
}

# Function to start ingestion
start_ingestion() {
    local attempt=$1
    local log_file="$LOG_DIR/ingest_$(date +%Y%m%d_%H%M%S)_attempt_${attempt}.log"
    
    log "Starting ingestion attempt $attempt (Log: $log_file)"
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Start ingestion in background
    nohup python main.py ingest-config > "$log_file" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    log "Ingestion started with PID: $pid"
    
    # Monitor the process
    local start_time=$(date +%s)
    local timeout=7200  # 2 hours timeout
    
    while [ $(($(date +%s) - start_time)) -lt $timeout ]; do
        if ! ps -p "$pid" > /dev/null 2>&1; then
            # Process finished
            local exit_code=$(tail -n 1 "$log_file" | grep -o "exit code: [0-9]*" | cut -d' ' -f3 || echo "unknown")
            if [ "$exit_code" = "0" ] || grep -q "✅ Ingestion completed" "$log_file"; then
                success "Ingestion completed successfully"
                rm -f "$PID_FILE"
                return 0
            else
                error "Ingestion failed with exit code: $exit_code"
                rm -f "$PID_FILE"
                return 1
            fi
        fi
        
        # Show progress every 30 seconds
        if [ $(( $(date +%s) % 30 )) -eq 0 ]; then
            log "Ingestion still running... (PID: $pid)"
            tail -n 5 "$log_file" | grep -E "(Processing|Upserted|✅|❌)" | tail -n 1 || true
        fi
        
        sleep 5
    done
    
    # Timeout reached
    error "Ingestion timed out after 2 hours"
    kill "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    return 1
}

# Main execution
main() {
    log "🚀 Starting robust ingestion script"
    log "Project directory: $PROJECT_DIR"
    log "Log directory: $LOG_DIR"
    
    # Kill any existing process
    kill_existing
    
    # Test Ollama connection
    if ! test_ollama; then
        error "Ollama connection failed. Exiting."
        exit 1
    fi
    
    # Reset collection
    reset_collection
    
    # Start ingestion with retries
    for attempt in $(seq 1 $MAX_RETRIES); do
        log "=== Starting ingestion attempt $attempt/$MAX_RETRIES ==="
        
        if start_ingestion $attempt; then
            success "Ingestion completed successfully on attempt $attempt"
            exit 0
        else
            error "Ingestion failed on attempt $attempt"
            
            if [ $attempt -lt $MAX_RETRIES ]; then
                warning "Waiting $RETRY_DELAY seconds before retry..."
                sleep $RETRY_DELAY
                
                # Reset collection before retry
                reset_collection
            fi
        fi
    done
    
    error "All ingestion attempts failed. Check logs in $LOG_DIR"
    exit 1
}

# Handle script termination
cleanup() {
    log "Cleaning up..."
    kill_existing
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run main function
main "$@" 