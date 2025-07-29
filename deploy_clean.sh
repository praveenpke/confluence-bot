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
VENV_DIR="/mnt/data/venv"
CACHE_DIR="/mnt/data/pip-cache"

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
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo mkdir -p $REMOTE_DIR $VENV_DIR $CACHE_DIR" --quiet
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo chown -R elp-chat:elp-chat $REMOTE_DIR $VENV_DIR $CACHE_DIR" --quiet

# Create a clean deployment package using tar
echo "📦 Creating clean deployment package..."
cd /Users/praveen/Desktop/elp-projects/ai_projects
tar --exclude='confluence-bot/__pycache__' \
    --exclude='confluence-bot/*.pyc' \
    --exclude='confluence-bot/.git' \
    --exclude='confluence-bot/.DS_Store' \
    --exclude='confluence-bot/*.log' \
    --exclude='confluence-bot/deploy*.sh' \
    --exclude='confluence-bot/.deployignore' \
    --exclude='confluence-bot/*.tar.gz' \
    --exclude='confluence-bot/*.zip' \
    --exclude='confluence-bot/test_*.py' \
    --exclude='confluence-bot/debug_*.py' \
    --exclude='confluence-bot/.vscode' \
    --exclude='confluence-bot/.idea' \
    -czf confluence-bot.tar.gz confluence-bot/

# Copy clean package to instance
echo "📁 Copying clean project files..."
gcloud compute scp confluence-bot.tar.gz $INSTANCE_NAME:/tmp/ --zone=$ZONE --quiet

# Extract and setup everything on the instance
echo "📁 Extracting files and setting up environment..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
set -e
echo 'Extracting project files...'
cd /tmp
sudo tar -xzf confluence-bot.tar.gz
sudo cp -r confluence-bot/* $REMOTE_DIR/
sudo chown -R elp-chat:elp-chat $REMOTE_DIR
sudo rm -rf /tmp/confluence-bot*

echo 'Setting up Python virtual environment...'
cd $REMOTE_DIR
sudo -u elp-chat python3 -m venv $VENV_DIR

echo 'Installing core Python dependencies...'
sudo -u elp-chat $VENV_DIR/bin/pip install --cache-dir $CACHE_DIR --no-cache-dir qdrant-client==1.7.0 requests==2.31.0 python-dotenv==1.0.0 PyPDF2==3.0.1 flask==3.0.0 flask-cors==4.0.0 beautifulsoup4==4.12.2

echo 'Installing sentence-transformers (this may take a while)...'
sudo -u elp-chat TMPDIR=$CACHE_DIR $VENV_DIR/bin/pip install --cache-dir $CACHE_DIR --no-cache-dir sentence-transformers==2.2.2 || echo 'Warning: sentence-transformers installation failed, will retry later'

echo 'Setting up Qdrant with persistent storage...'
sudo mkdir -p /mnt/data/qdrant
sudo docker run -d --name qdrant -p 6333:6333 -v /mnt/data/qdrant:/qdrant/storage qdrant/qdrant
sudo docker update --restart=always qdrant

echo 'Creating systemd service...'
sudo tee /etc/systemd/system/elp-chat.service > /dev/null << 'EOF'
[Unit]
Description=ELP Confluence Q&A Bot
After=network.target docker.service

[Service]
Type=simple
User=elp-chat
WorkingDirectory=$REMOTE_DIR
Environment=PATH=$VENV_DIR/bin
Environment=TMPDIR=$CACHE_DIR
ExecStart=$VENV_DIR/bin/python start_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo 'Starting service...'
sudo systemctl daemon-reload
sudo systemctl enable elp-chat
sudo systemctl start elp-chat

echo 'Waiting for service to start...'
sleep 10

echo 'Checking service status...'
sudo systemctl status elp-chat --no-pager
" --quiet

# Clean up local tar file
rm -f confluence-bot.tar.gz

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
echo ""
echo "⚠️  Note: If sentence-transformers failed to install, run this command later:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd $REMOTE_DIR && sudo -u elp-chat $VENV_DIR/bin/pip install sentence-transformers==2.2.2'" 