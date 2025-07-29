from src.ollama_client import get_embedding
from src.vector_store import query_similar, get_answer, set_context_config, get_context_config
from src.config_loader import update_config_section, get_config_value

def main():
    print("🤖 ELP Chat Q&A Bot")
    print("Commands:")
    print("  'exit' - quit")
    print("  'config' - see current settings")
    print("  'set-top-k <number>' - adjust number of documents retrieved")
    print("  'set-context-length <number>' - adjust LLM context length")
    print("  'set-max-chars <number>' - adjust max context characters")
    print("  'reload-config' - reload configuration from file")
    
    while True:
        query = input("\nAsk me anything from Confluence: ").strip()
        if not query:
            print("⚠️ Please enter a valid query.")
            continue
        if query.lower() == 'exit':
            print("👋 Goodbye!")
            break
        if query.lower() == 'config':
            config = get_context_config()
            print(f"\n📊 Current Configuration:")
            print(f"  Documents retrieved: {config['top_k']}")
            print(f"  Context length (tokens): {config['context_length']}")
            print(f"  Max context chars: {config['max_context_chars']}")
            
            # Also show config file values
            top_k_file = get_config_value("context_settings", "default_top_k")
            context_length_file = get_config_value("context_settings", "default_context_length")
            max_chars_file = get_config_value("context_settings", "max_context_chars")
            print(f"\n📁 Config file values:")
            print(f"  Documents retrieved: {top_k_file}")
            print(f"  Context length (tokens): {context_length_file}")
            print(f"  Max context chars: {max_chars_file}")
            continue
            
        if query.lower().startswith('set-top-k '):
            try:
                new_top_k = int(query.split()[1])
                set_context_config(top_k=new_top_k)
                continue
            except (IndexError, ValueError):
                print("⚠️ Usage: 'set-top-k <number>' (e.g., 'set-top-k 15')")
                continue
                
        if query.lower().startswith('set-context-length '):
            try:
                new_length = int(query.split()[1])
                set_context_config(context_length=new_length)
                continue
            except (IndexError, ValueError):
                print("⚠️ Usage: 'set-context-length <number>' (e.g., 'set-context-length 32768')")
                continue
                
        if query.lower().startswith('set-max-chars '):
            try:
                new_chars = int(query.split()[1])
                set_context_config(max_context_chars=new_chars)
                continue
            except (IndexError, ValueError):
                print("⚠️ Usage: 'set-max-chars <number>' (e.g., 'set-max-chars 100000')")
                continue
                
        if query.lower() == 'reload-config':
            print("🔄 Reloading configuration from file...")
            # This will reload on next query since config is loaded at module level
            print("✅ Configuration will be reloaded on next query")
            continue
            
        print("🔍 Searching for relevant documents...")
        vector = get_embedding(query)
        if not vector:
            print("❌ No embedding returned. Check model or input.")
            continue
            
        context_docs = query_similar(vector)
        
        if not context_docs:
            print("❌ No relevant documents found.")
            continue
        
        # Show sources with better metadata extraction
        print("\n📚 Sources:")
        for i, doc in enumerate(context_docs, 1):
            # Try different possible title fields
            title = (doc.payload.get("page_title") or 
                    doc.payload.get("title") or 
                    doc.payload.get("attachment_title") or 
                    "Unknown")
            
            url = doc.payload.get("url", "")
            content_type = doc.payload.get("content_type", "page")
            space_name = doc.payload.get("space_name", "")
            
            # Format the source display
            source_info = f"  {i}. {title}"
            if space_name:
                source_info += f" (Space: {space_name})"
            if content_type == "pdf_attachment":
                source_info += " [PDF]"
            print(source_info)
            
            if url:
                print(f"     URL: {url}")
        
        print("\n🤖 Generating answer...")
        answer = get_answer(query, context_docs)
        print(f"\n🧠 Answer: {answer}")

if __name__ == "__main__":
    main()
