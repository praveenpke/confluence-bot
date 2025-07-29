# ELP Confluence Q&A Bot

A conversational AI bot that can answer questions about your Confluence documentation using vector search and Ollama. This bot is specifically designed for the ELP Aviation Crew Rules system but can be adapted for other Confluence spaces.

## 🚀 Quick Start

### **Local Development:**
```bash
# Install dependencies
pip install -r requirements.txt

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Start Ollama (install first if needed)
ollama pull llama2
ollama pull nomic-embed-text

# Configure environment
cp .env.template .env
# Edit .env with your Confluence credentials

# Ingest documents
python main.py ingest-config

# Start web interface
python main.py web
```

### **Production Deployment:**
```bash
# Deploy to Google Cloud (one command)
./deploy_clean.sh

# Access at: http://[EXTERNAL_IP]:5001
```

## ✨ Features

- 🔗 **Confluence Integration**: Pull documents directly from Confluence API
- 🧠 **Vector Search**: Use embeddings to find relevant context
- 🤖 **LLM Responses**: Generate answers using Ollama (llama2 model)
- 📊 **Local Vector Database**: Store embeddings in Qdrant
- 🔍 **Source Attribution**: See which Confluence pages were used for answers
- 📎 **PDF Support**: Extract and process PDF attachments from Confluence
- ⚙️ **Configurable Context**: Adjust context size and retrieval parameters
- 🎯 **Nested Pages**: Automatically discover and ingest nested page hierarchies
- 🔧 **Configuration Management**: Easy-to-use config system for customization
- 🌐 **Web Interface**: Modern ChatGPT-style UI with streaming responses
- 🚀 **Production Ready**: Systemd service, auto-restart, firewall rules

## 📋 Prerequisites

### **Local Development:**
1. **Python 3.8+** with pip
2. **Docker** (for Qdrant)
3. **Ollama** with llama2 and nomic-embed-text models
4. **Confluence API** access (token and credentials)

### **Production Deployment:**
1. **Google Cloud CLI** installed and configured
2. **GCP Instance**: `elp-chat-instance` in zone `us-central1-c`
3. **External Ollama endpoint** (for LLM and embeddings)

## 🛠️ Local Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
Create a `.env` file:
```bash
# Confluence Configuration
CONFLUENCE_BASE_URL=https://elpaviation.atlassian.net
CONFLUENCE_USERNAME=your-email@domain.com
CONFLUENCE_API_TOKEN=your-api-token

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
```

### 3. Configure Spaces
Edit `config/spaces.json` to specify which Confluence spaces to ingest:
```json
[
  {
    "key": "SPACE_KEY",
    "name": "Space Name"
  }
]
```

### 4. Start Required Services
```bash
# Start Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# Start Ollama (install first if needed)
ollama pull llama2
ollama pull nomic-embed-text
```

## 🚀 Production Deployment

### **One-Command Deployment:**
```bash
# Deploy to Google Cloud
./deploy_clean.sh
```

### **Manual Deployment Steps:**
```bash
# 1. Set Google Cloud project
gcloud config set project balmy-cab-466902-a7

# 2. Start instance
gcloud compute instances start elp-chat-instance --zone=us-central1-c

# 3. Deploy application
./deploy_clean.sh

# 4. Access application
# URL: http://[EXTERNAL_IP]:5001
```

### **Server Management (SSH):**
```bash
# SSH to instance
gcloud compute ssh elp-chat-instance --zone=us-central1-c

# Start server
sudo systemctl start elp-chat

# Stop server
sudo systemctl stop elp-chat

# Restart server
sudo systemctl restart elp-chat

# Check status
sudo systemctl status elp-chat

# View logs
sudo journalctl -u elp-chat -f

# Test web interface
curl http://localhost:5001
```

## 📖 Usage

### **Test Confluence Connection:**
```bash
python main.py test
```

### **Ingest Documents:**
```bash
# Ingest from configured spaces (recommended)
python main.py ingest-config

# Ingest all pages from a specific space
python main.py ingest SPACE_KEY

# Ingest from local docs folder
python main.py ingest-local
```

### **Interactive Q&A:**
```bash
python main.py query
```

### **Web Interface:**
```bash
python main.py web
```
**Access at:** http://localhost:5001

### **Configuration:**
```bash
python main.py config
```

### **Get Help:**
```bash
python main.py help
```

## 🌐 Web Interface Features

The web interface provides a modern ChatGPT-style experience:

### **UI Features:**
- **Dark Theme**: Modern dark background with clean typography
- **Rounded Messages**: Soft, modern message bubbles
- **Settings Icon**: ⚙️ icon for configuration popup
- **AI Glow Input**: Animated input box with glow effects
- **Send Button**: Integrated send button in input field

### **Interaction Features:**
- **Enter to Send**: Press Enter to send messages
- **Streaming Responses**: Real-time character-by-character display
- **Markdown Rendering**: Proper formatting of headers, lists, code blocks
- **Source Links**: Clickable links to original Confluence pages
- **Configuration Panel**: Real-time settings adjustment

### **Technical Features:**
- **Input Protection**: Disabled during processing
- **Auto-scrolling**: Chat window follows conversation
- **Error Handling**: Graceful error messages
- **Responsive Design**: Works on all devices

## ⚙️ Configuration

### **Q&A Bot Settings (`config/qa_config.json`):**
```json
{
  "context_settings": {
    "default_top_k": 5,
    "default_context_length": 32768,
    "max_context_chars": 150000
  },
  "model_settings": {
    "llm_model": "llama2",
    "embedding_model": "nomic-embed-text",
    "ollama_url": "http://localhost:11434"
  },
  "prompt_settings": {
    "system_prompt": "You are an AI assistant for the ELP Aviation Crew Rules software system...",
    "instruction": "Answer the question based ONLY on the provided context..."
  }
}
```

### **Configuration Parameters:**
- **default_top_k**: Number of documents to retrieve (default: 5)
- **default_context_length**: Token limit for LLM context (default: 32768)
- **max_context_chars**: Maximum characters in context (default: 150000)
- **enable_debug_logging**: Enable detailed debug output (default: true)

## 🔧 Management Commands

### **Local Cleanup:**
```bash
# Clean local directory
./clean_local.sh

# Manual cleanup
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### **Service Management (Production):**
```bash
# Check status
gcloud compute ssh elp-chat-instance --zone=us-central1-c --command="sudo systemctl status elp-chat"

# View logs
gcloud compute ssh elp-chat-instance --zone=us-central1-c --command="sudo journalctl -u elp-chat -f"

# Restart service
gcloud compute ssh elp-chat-instance --zone=us-central1-c --command="sudo systemctl restart elp-chat"
```

### **Application Management:**
```bash
# SSH to instance
gcloud compute ssh elp-chat-instance --zone=us-central1-c

# Run commands as elp-chat user
sudo -u elp-chat /home/elp-chat/venv/bin/python main.py help
sudo -u elp-chat /home/elp-chat/venv/bin/python main.py ingest-config
sudo -u elp-chat /home/elp-chat/venv/bin/python main.py query
```

## 📁 File Structure

```
confluence-bot/
├── main.py                 # Main orchestrator
├── web_app.py              # Flask web application
├── start_web.py            # Web server starter
├── edit_config.py          # Configuration editor
├── requirements.txt        # Python dependencies
├── deploy_clean.sh         # Clean deployment script
├── clean_local.sh          # Local cleanup script
├── .gitignore              # Git exclusions
├── .deployignore           # Deployment exclusions
├── templates/              # Web templates
│   └── index.html         # Chat interface template
├── src/                   # Core modules
│   ├── query.py           # Q&A interface
│   ├── vector_store.py    # Vector database operations
│   ├── config_loader.py   # Configuration management
│   ├── ollama_client.py   # LLM client
│   ├── confluence_client.py # Confluence API client
│   ├── ingest.py          # Document ingestion
│   └── format_response.py # Response formatting
└── config/                # Configuration files
    ├── qa_config.json     # Q&A bot settings
    └── spaces.json        # Confluence spaces config
```

## 🔍 Troubleshooting

### **Common Issues:**

1. **Confluence Connection Failed**
   - Verify API token is correct
   - Check Confluence URL accessibility
   - Ensure username is email address

2. **Ollama Connection Failed**
   - Make sure Ollama is running: `ollama serve`
   - Verify models are installed: `ollama list`

3. **Qdrant Connection Failed**
   - Ensure Qdrant is running on port 6333
   - Check Docker container status

4. **Poor Answer Quality**
   - Increase `default_top_k` (try 8-12)
   - Increase `default_context_length` (try 32768)
   - Increase `max_context_chars` (try 150000)

5. **Memory Issues**
   - Reduce `max_context_chars` (try 100000)
   - Reduce `default_top_k` (try 3-5)
   - Reduce `default_context_length` (try 16384)

### **Production Issues:**

1. **Port 5001 not accessible**
   ```bash
   sudo ufw allow 5001/tcp
   ```

2. **Service not starting**
   ```bash
   sudo journalctl -u elp-chat -f
   ```

3. **Missing dependencies**
   ```bash
   sudo -u elp-chat /home/elp-chat/venv/bin/pip install -r /home/elp-chat/confluence-bot/requirements.txt
   ```

## 🎯 Performance Tips

- **Context Size**: Start with `default_top_k: 5` and adjust based on answer quality
- **Token Limits**: Use `default_context_length: 32768` for llama2
- **Memory**: Monitor memory usage and reduce `max_context_chars` if needed
- **Ingestion**: Use `ingest-config` for production use
- **Web Interface**: Use settings popup (⚙️) to adjust parameters in real-time

## 🔐 Security Notes

- **Environment Variables**: Never commit `.env` files to version control
- **API Tokens**: Use environment variables for sensitive credentials
- **Firewall**: Only open necessary ports (5001 for web interface)
- **External Ollama**: Use secure endpoints for production deployments

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review service logs: `sudo journalctl -u elp-chat -f`
3. Test local setup before deploying to production
4. Verify all prerequisites are met

## 📄 License

This project is designed for internal use at ELP Aviation. 