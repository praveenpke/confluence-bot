# Confluence Q&A Bot

A conversational AI bot that can answer questions about your Confluence documentation using vector search and Ollama. This bot is specifically designed for the ELP Aviation Crew Rules system but can be adapted for other Confluence spaces.

## Features

- 🔗 **Confluence Integration**: Pull documents directly from Confluence API
- 🧠 **Vector Search**: Use embeddings to find relevant context
- 🤖 **LLM Responses**: Generate answers using Ollama (llama2 model)
- 📊 **Local Vector Database**: Store embeddings in Qdrant
- 🔍 **Source Attribution**: See which Confluence pages were used for answers
- 📎 **PDF Support**: Extract and process PDF attachments from Confluence
- ⚙️ **Configurable Context**: Adjust context size and retrieval parameters
- 🎯 **Nested Pages**: Automatically discover and ingest nested page hierarchies
- 🔧 **Configuration Management**: Easy-to-use config system for customization

## Prerequisites

1. **Qdrant Vector Database**: Running locally on port 6333
2. **Ollama**: Running locally with llama2 and nomic-embed-text models
3. **Confluence Access**: API token and credentials

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project directory:

```bash
# Confluence Configuration
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@domain.com
CONFLUENCE_API_TOKEN=your-api-token

# Qdrant Configuration (optional - defaults shown)
QDRANT_HOST=localhost
QDRANT_PORT=6333
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

**Qdrant:**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

**Ollama:**
```bash
# Install Ollama first, then pull models
ollama pull llama2
ollama pull nomic-embed-text
```

## Usage

### Test Confluence Connection

```bash
python main.py test
```

### Ingest Documents from Confluence

```bash
# Ingest from configured spaces (recommended)
python main.py ingest-config

# Ingest all pages from a specific space
python main.py ingest SPACE_KEY

# Ingest from local docs folder
python main.py ingest-local
```

### Start Interactive Q&A

```bash
python main.py query
```

### Configure Q&A Bot Settings

```bash
python main.py config
```

### Get Help

```bash
python main.py help
```

## Q&A Bot Commands

When using the interactive Q&A session, you can use these commands:

- `exit` - Quit the session
- `config` - Show current configuration settings
- `set-top-k <number>` - Adjust number of documents retrieved (e.g., `set-top-k 15`)
- `set-context-length <number>` - Adjust LLM context length (e.g., `set-context-length 32768`)
- `set-max-chars <number>` - Adjust max context characters (e.g., `set-max-chars 100000`)
- `reload-config` - Reload configuration from file

## Configuration

The bot uses a JSON configuration file (`config/qa_config.json`) for easy customization:

```json
{
  "context_settings": {
    "default_top_k": 10,
    "default_context_length": 16384,
    "max_context_chars": 50000
  },
  "model_settings": {
    "llm_model": "llama2",
    "embedding_model": "nomic-embed-text"
  },
  "prompt_settings": {
    "system_prompt": "You are an AI assistant for the ELP Aviation Crew Rules software system...",
    "instruction": "Answer the question based ONLY on the provided context..."
  },
  "debug_settings": {
    "enable_debug_logging": true,
    "show_context_preview": true,
    "show_document_details": true
  }
}
```

### Configuration Parameters

- **default_top_k**: Number of documents to retrieve for context (default: 10)
- **default_context_length**: Token limit for LLM context (default: 16384)
- **max_context_chars**: Maximum characters in context to prevent overflow (default: 50000)
- **enable_debug_logging**: Enable detailed debug output (default: true)

## How It Works

1. **Ingestion**: 
   - Documents are pulled from configured Confluence spaces
   - PDF attachments are automatically extracted and processed
   - Nested page hierarchies are discovered and included
   - Content is converted to embeddings using Ollama's `nomic-embed-text` model

2. **Storage**: 
   - Embeddings are stored in Qdrant vector database with metadata
   - Each document gets a unique ID to prevent overwrites

3. **Query**: 
   - User questions are converted to embeddings
   - Similar documents are retrieved based on configurable `top_k` parameter
   - Context is assembled from retrieved documents

4. **Answer**: 
   - Retrieved context is sent to Ollama's `llama2` model
   - Model generates answers based on provided context only
   - Sources are attributed to specific Confluence pages

## File Structure

```
confluence-bot/
├── main.py                 # Main orchestrator
├── edit_config.py          # Configuration editor
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── src/                   # Core modules
│   ├── query.py           # Q&A interface
│   ├── vector_store.py    # Vector database operations
│   ├── config_loader.py   # Configuration management
│   ├── ollama_client.py   # LLM client
│   ├── confluence_client.py # Confluence API client
│   └── ingest.py          # Document ingestion
└── config/                # Configuration files
    ├── qa_config.json     # Q&A bot settings
    └── spaces.json        # Confluence spaces config
```

## Troubleshooting

### Common Issues

1. **Confluence Connection Failed**
   - Verify your API token is correct
   - Check that your Confluence URL is accessible
   - Ensure your username is your email address

2. **Ollama Connection Failed**
   - Make sure Ollama is running: `ollama serve`
   - Verify models are installed: `ollama list`

3. **Qdrant Connection Failed**
   - Ensure Qdrant is running on port 6333
   - Check Docker container status

4. **Poor Answer Quality**
   - Increase `default_top_k` in configuration
   - Increase `default_context_length` for more context
   - Check if relevant documents were ingested

5. **Memory Issues**
   - Reduce `max_context_chars` in configuration
   - Reduce `default_top_k` to retrieve fewer documents

### Getting Confluence API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name and copy the token
4. Use your email as username and the token as password

## Performance Tips

- **Context Size**: Start with `default_top_k: 10` and adjust based on answer quality
- **Token Limits**: Use `default_context_length: 16384` for llama2, adjust for other models
- **Memory**: Monitor memory usage and reduce `max_context_chars` if needed
- **Ingestion**: Use `ingest-config` for production use, it handles nested pages better

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is designed for internal use at ELP Aviation. 