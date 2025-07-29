#!/bin/bash

echo "🚀 Clean Ollama Setup for RunPod"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Clean up any existing Ollama
log "Cleaning up existing Ollama..."
pkill ollama 2>/dev/null || true
sleep 3

# Step 1: Check system
log "Step 1: Checking system..."
if command -v nvidia-smi &> /dev/null; then
    log "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
    success "GPU detected"
else
    error "NVIDIA GPU not detected"
    exit 1
fi

if [ -d "/workspace" ]; then
    log "Volume: $(df -h /workspace | tail -1 | awk '{print $2 " available"}')"
    success "Volume mounted"
else
    error "Volume not mounted"
    exit 1
fi

# Step 2: Install Ollama
log "Step 2: Installing Ollama..."
if command -v ollama &> /dev/null; then
    warning "Ollama already installed"
else
    curl -fsSL https://ollama.ai/install.sh | sh
    success "Ollama installed"
fi

# Step 3: Configure for port 5123
log "Step 3: Configuring Ollama for port 5123..."
mkdir -p /etc/ollama
tee /etc/ollama/ollama.json > /dev/null << 'EOF'
{
  "host": "0.0.0.0:5123",
  "data": "/workspace/ollama"
}
EOF

mkdir -p /workspace/ollama
chown -R root:root /workspace/ollama
success "Configuration created"

# Step 4: Start Ollama
log "Step 4: Starting Ollama on port 5123..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to start
log "Waiting for Ollama to start..."
for i in {1..30}; do
    if curl -s http://localhost:5123/api/tags > /dev/null 2>&1; then
        success "Ollama started on port 5123"
        break
    fi
    if [ $i -eq 30 ]; then
        error "Ollama failed to start"
        exit 1
    fi
    sleep 1
done

# Step 5: Pull models
log "Step 5: Pulling models (15-30 minutes)..."
ollama pull nomic-embed-text
success "nomic-embed-text pulled"

ollama pull llama2:13b
success "llama2:13b pulled"

ollama pull codellama:13b
success "codellama:13b pulled"

# Step 6: Test setup
log "Step 6: Testing setup..."
RESPONSE=$(curl -s -X POST http://localhost:5123/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "prompt": "Test"}')

if echo "$RESPONSE" | grep -q "embedding"; then
    success "API test passed"
else
    error "API test failed"
fi

# Step 7: Get public IP
PUBLIC_IP=$(curl -s ifconfig.me)
log "Public IP: $PUBLIC_IP"

# Step 8: Summary
echo ""
echo "=================================="
success "Ollama setup completed!"
echo ""
echo "🎯 IMPORTANT: Add port mapping in RunPod dashboard:"
echo "   - External Port: 5123"
echo "   - Internal Port: 5123"
echo "   - Protocol: TCP"
echo ""
echo "📋 After adding port mapping:"
echo "1. Update confluence-bot .env:"
echo "   OLLAMA_URL=http://$PUBLIC_IP:5123"
echo ""
echo "2. Test external access:"
echo "   curl -X POST http://$PUBLIC_IP:5123/api/embeddings \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"model\": \"nomic-embed-text\", \"prompt\": \"Test\"}'"
echo ""
echo "3. Run ingestion:"
echo "   python main.py ingest-config"
echo ""
echo "📊 Monitoring:"
echo "  - Check status: ps aux | grep ollama"
echo "  - Kill if needed: pkill ollama"
echo "  - Restart: ollama serve &"
echo "=================================="

success "Setup completed! 🚀" 