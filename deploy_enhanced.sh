#!/bin/bash

# Enhanced Deployment Script for Confluence Bot
# Includes background ingestion and improved error handling

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID="balmy-cab-466902-a7"
INSTANCE_NAME="elp-chat-instance"
ZONE="us-central1-c"
REMOTE_DIR="/mnt/data/confluence-bot"
VENV_DIR="/mnt/data/venv"
CACHE_DIR="/mnt/data/pip-cache"

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

# Step 1: Create deployment package
log "Step 1: Creating deployment package..."
tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' --exclude='*.log' --exclude='progress' -czf confluence-bot-enhanced.tar.gz .

if [ $? -eq 0 ]; then
    success "Deployment package created"
else
    error "Failed to create deployment package"
    exit 1
fi

# Step 2: Upload to GCP instance
log "Step 2: Uploading to GCP instance..."
gcloud compute scp confluence-bot-enhanced.tar.gz ${INSTANCE_NAME}:${REMOTE_DIR}/ --zone=${ZONE}

if [ $? -eq 0 ]; then
    success "Package uploaded to GCP"
else
    error "Failed to upload package"
    exit 1
fi

# Step 3: Deploy and setup on GCP
log "Step 3: Deploying on GCP instance..."
gcloud compute ssh ${INSTANCE_NAME} --zone=${ZONE} --command="
set -e

cd ${REMOTE_DIR}

# Backup existing files
log 'Backing up existing files...'
if [ -d 'backup' ]; then
    rm -rf backup
fi
mkdir -p backup
cp -r * backup/ 2>/dev/null || true

# Extract new package
log 'Extracting new package...'
tar -xzf confluence-bot-enhanced.tar.gz
rm confluence-bot-enhanced.tar.gz

# Set permissions
log 'Setting permissions...'
chown -R elp-chat:elp-chat ${REMOTE_DIR}
chmod +x *.py *.sh

# Activate virtual environment and install dependencies
log 'Installing dependencies...'
source ${VENV_DIR}/bin/activate
export TMPDIR=${CACHE_DIR}
pip install --cache-dir ${CACHE_DIR} --no-cache-dir -r requirements.txt

# Create necessary directories
log 'Creating directories...'
mkdir -p progress logs

# Test the new system
log 'Testing new system...'
python -c 'from src.vector_store import collection_exists, create_collection; print(\"✅ Vector store functions working\")'
python -c 'from background_ingest import BackgroundIngestion; print(\"✅ Background ingestion system working\")'

success 'Deployment completed successfully!'
"

if [ $? -eq 0 ]; then
    success "Deployment completed"
else
    error "Deployment failed"
    exit 1
fi

# Step 4: Start background ingestion
log "Step 4: Starting background ingestion..."
gcloud compute ssh ${INSTANCE_NAME} --zone=${ZONE} --command="
cd ${REMOTE_DIR}
source ${VENV_DIR}/bin/activate

# Kill any existing ingestion processes
pkill -f 'python.*ingest' || true
sleep 2

# Start background ingestion
log 'Starting background ingestion...'
nohup python background_ingest.py start --incremental > logs/background_ingest.log 2>&1 &
echo \$! > /tmp/background_ingest.pid

success 'Background ingestion started'
"

if [ $? -eq 0 ]; then
    success "Background ingestion started"
else
    error "Failed to start background ingestion"
fi

# Step 5: Check web interface
log "Step 5: Checking web interface..."
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://34.134.43.0:5001 || echo "000")

if [ "$WEB_STATUS" = "200" ]; then
    success "Web interface is accessible at http://34.134.43.0:5001"
else
    warning "Web interface may not be accessible. Status: $WEB_STATUS"
fi

# Step 6: Show status
log "Step 6: System status..."
gcloud compute ssh ${INSTANCE_NAME} --zone=${ZONE} --command="
cd ${REMOTE_DIR}
source ${VENV_DIR}/bin/activate

echo '📊 System Status:'
echo '================'

# Check background ingestion
if [ -f /tmp/background_ingest.pid ]; then
    PID=\$(cat /tmp/background_ingest.pid)
    if ps -p \$PID > /dev/null 2>&1; then
        echo '✅ Background ingestion: Running (PID: '\$PID')'
    else
        echo '❌ Background ingestion: Not running'
    fi
else
    echo '❌ Background ingestion: PID file not found'
fi

# Check web interface
if ps aux | grep -q 'start_web.py'; then
    echo '✅ Web interface: Running'
else
    echo '❌ Web interface: Not running'
fi

# Check collection stats
python -c '
from src.vector_store import get_collection_stats
stats = get_collection_stats()
if stats:
    print(f\"✅ Vector store: {stats.get(\"points_count\", 0)} documents\")
else:
    print(\"❌ Vector store: Not available\")
'

echo ''
echo '🌐 Access your system:'
echo '   Web Interface: http://34.134.43.0:5001'
echo '   SSH Access: gcloud compute ssh elp-chat-instance --zone=us-central1-c'
echo ''
echo '📋 Useful commands:'
echo '   Check status: python background_ingest.py status'
echo '   Stop ingestion: python background_ingest.py stop'
echo '   Test query: python main.py query'
echo '   View logs: tail -f logs/background_ingest.log'
"

# Cleanup
rm -f confluence-bot-enhanced.tar.gz

success "Enhanced deployment completed! 🚀"
echo ""
echo "🎯 Next steps:"
echo "1. Access web interface: http://34.134.43.0:5001"
echo "2. Test queries while ingestion runs in background"
echo "3. Monitor progress: tail -f logs/background_ingest.log"
echo "4. Check status: python background_ingest.py status" 