#!/bin/bash

# Clean Deployment Script for ELP Confluence Bot
# This script deploys the exact working local structure to GCP

set -e

echo "🚀 Starting clean deployment to GCP..."

# Configuration
INSTANCE_NAME="elp-chat-instance"
ZONE="us-central1-c"
PROJECT_ID="balmy-cab-466902-a7"
REMOTE_DIR="/mnt/data/confluence-bot"

# Set the project
echo "📋 Setting Google Cloud project..."
gcloud config set project $PROJECT_ID

# Start instance if not running
echo "🔧 Starting GCP instance..."
gcloud compute instances start $INSTANCE_NAME --zone=$ZONE

# Wait for instance to be ready
echo "⏳ Waiting for instance to be ready..."
sleep 30

# Test SSH connection
echo "🔌 Testing SSH connection..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="echo 'Instance is ready'" --quiet

# Stop services and clean up
echo "🛑 Stopping services and cleaning up..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo systemctl stop elp-chat 2>/dev/null || true" --quiet
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo docker stop qdrant 2>/dev/null || true" --quiet
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo docker rm qdrant 2>/dev/null || true" --quiet

# Clean remote directory and old files
echo "🧹 Cleaning remote directory and old files..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo rm -rf $REMOTE_DIR/* /home/elp-chat/confluence-bot/* 2>/dev/null || true" --quiet
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo mkdir -p $REMOTE_DIR" --quiet

# Create a clean deployment package using rsync with exclude patterns
echo "📦 Creating clean deployment package..."
TEMP_DIR=$(mktemp -d)

# Use rsync to copy files while excluding unnecessary ones
rsync -av --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='*.pyo' \
         --exclude='.env' \
         --exclude='.git' \
         --exclude='.DS_Store' \
         --exclude='*.log' \
         --exclude='deploy*.sh' \
         --exclude='DEPLOYMENT_*.md' \
         --exclude='.deployignore' \
         --exclude='*.tar.gz' \
         --exclude='*.zip' \
         --exclude='test_*.py' \
         --exclude='debug_*.py' \
         --exclude='.vscode' \
         --exclude='.idea' \
         ./ $TEMP_DIR/

# Copy clean package to instance
echo "📁 Copying clean project files..."
gcloud compute scp --recurse $TEMP_DIR/* $INSTANCE_NAME:/tmp/confluence-bot --zone=$ZONE --quiet

# Clean up temp directory
rm -rf $TEMP_DIR

# Move files to correct location with proper permissions
echo "📁 Moving files to attached volume..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo cp -r /tmp/confluence-bot/* $REMOTE_DIR/ && sudo rm -rf /tmp/confluence-bot" --quiet

# Set correct permissions
echo "🔐 Setting permissions..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo chown -R elp-chat:elp-chat $REMOTE_DIR" --quiet

# Install dependencies
echo "📦 Installing Python dependencies..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="cd $REMOTE_DIR && sudo -u elp-chat /home/elp-chat/venv/bin/pip install -r requirements.txt" --quiet

# Setup Qdrant with persistent storage on attached volume
echo "🗄️ Setting up Qdrant with persistent storage..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo mkdir -p /mnt/data/qdrant" --quiet
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo docker run -d --name qdrant -p 6333:6333 -v /mnt/data/qdrant:/qdrant/storage qdrant/qdrant && sudo docker update --restart=always qdrant" --quiet

# Create systemd service
echo "⚙️ Creating systemd service..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo tee /etc/systemd/system/elp-chat.service > /dev/null << 'EOF'
[Unit]
Description=ELP Confluence Q&A Bot
After=network.target docker.service

[Service]
Type=simple
User=elp-chat
WorkingDirectory=$REMOTE_DIR
Environment=PATH=/home/elp-chat/venv/bin
ExecStart=/home/elp-chat/venv/bin/python start_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF" --quiet

# Enable and start service
echo "🚀 Starting service..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo systemctl daemon-reload && sudo systemctl enable elp-chat && sudo systemctl start elp-chat" --quiet

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo systemctl status elp-chat --no-pager" --quiet

# Get external IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Access your application at:"
echo "   http://$EXTERNAL_IP:5001"
echo ""
echo "📋 Next steps:"
echo "   1. Update the .env file with your Confluence credentials"
echo "   2. Update OLLAMA_URL in .env with your external Ollama endpoint"
echo "   3. Run ingestion: ssh to instance and run 'python main.py ingest-config'"
echo ""
echo "🔧 Management commands:"
echo "   - Check status: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='sudo systemctl status elp-chat'"
echo "   - View logs: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='sudo journalctl -u elp-chat -f'"
echo "   - Restart: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='sudo systemctl restart elp-chat'" 