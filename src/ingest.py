# src/ingest.py

import os
import json
from src.confluence_client import ConfluenceClient
from src.ollama_client import get_embedding
from src.vector_store import create_collection, upsert_embeddings
import requests

def load_config():
    """
    Load spaces configuration from config/spaces.json
    """
    config_path = os.path.join("config", "spaces.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return []

def get_all_nested_spaces(client, parent_space_key, max_depth=3, current_depth=0):
    """
    Recursively get all nested spaces from a parent space
    """
    if current_depth >= max_depth:
        return []
    
    try:
        # Get direct child spaces
        child_spaces = client.get_child_spaces(parent_space_key)
        
        all_spaces = []
        for child_space in child_spaces:
            space_info = {
                "key": child_space.get("key"),
                "name": child_space.get("name"),
                "type": child_space.get("type"),
                "parent_key": parent_space_key,
                "depth": current_depth + 1,
                "url": f"{client.base_url}/display/{child_space.get('key')}",
                "description": child_space.get("description", {}).get("plain", {}).get("value", ""),
                "status": child_space.get("status", "unknown")
            }
            all_spaces.append(space_info)
            
            # Recursively get nested spaces
            nested_spaces = get_all_nested_spaces(client, child_space.get("key"), max_depth, current_depth + 1)
            all_spaces.extend(nested_spaces)
        
        return all_spaces
    except Exception as e:
        print(f"Error getting nested spaces for {parent_space_key}: {e}")
        return []

def get_space_pages(client, space_key, limit=None):
    """
    Get pages from a specific space with limit (removed limit to get ALL pages)
    """
    try:
        pages = client.get_all_pages(space_key=space_key, limit=limit)
        return pages
    except Exception as e:
        print(f"Error getting pages for space {space_key}: {e}")
        return []

def get_child_pages(client, page_id):
    """
    Get all child pages of a parent page
    """
    try:
        url = f"{client.base_url}/rest/api/content/{page_id}/child/page"
        params = {
            "limit": 1000,
            "expand": "version,space"
        }
        
        response = requests.get(url, headers=client.headers)
        response.raise_for_status()
        
        data = response.json()
        return data.get("results", [])
        
    except Exception as e:
        print(f"Error getting child pages for {page_id}: {e}")
        return []

def get_all_pages_recursive(client, space_key, limit=None):
    """
    Get all pages from a space including nested child pages recursively
    """
    all_pages = []
    
    # Get top-level pages
    print(f"      🔍 Getting top-level pages for space {space_key}...")
    top_level_pages = client.get_all_pages(space_key=space_key, limit=limit)
    print(f"      📄 Found {len(top_level_pages)} top-level pages")
    all_pages.extend(top_level_pages)
    
    # Recursively get child pages
    def get_children_recursive(parent_pages, level=1):
        for parent_page in parent_pages:
            print(f"      🔍 Getting child pages for: {parent_page.get('title', 'Unknown')} (Level {level})")
            child_pages = get_child_pages(client, parent_page.get("id"))
            if child_pages:
                print(f"      📄 Found {len(child_pages)} child pages for: {parent_page.get('title', 'Unknown')}")
                all_pages.extend(child_pages)
                # Recursively get children of children
                get_children_recursive(child_pages, level + 1)
            else:
                print(f"      📄 No child pages for: {parent_page.get('title', 'Unknown')}")
    
    get_children_recursive(top_level_pages)
    
    print(f"      📊 Total pages found (including nested): {len(all_pages)}")
    return all_pages

def ingest_from_config():
    """
    Ingest documents from configured spaces including all nested spaces and PDF attachments
    """
    try:
        print("📋 Loading configuration...")
        config_spaces = load_config()
        
        if not config_spaces:
            print("❌ No spaces found in config file")
            return
        
        print(f"🔗 Connecting to Confluence...")
        client = ConfluenceClient()
        
        print(f"📚 Found {len(config_spaces)} configured spaces")
        
        # Create collection if it doesn't exist
        create_collection()
        
        all_spaces_to_process = []
        processed_spaces = []  # Track processed spaces for verification
        
        # Process each configured space
        for config_space in config_spaces:
            space_key = config_space.get("key")
            space_name = config_space.get("name")
            
            print(f"\n🌐 Processing configured space: {space_name} ({space_key})")
            
            # Add the main configured space
            main_space = {
                "key": space_key,
                "name": space_name,
                "type": config_space.get("type", "global"),
                "parent_key": None,
                "depth": 0,
                "url": config_space.get("url", f"{client.base_url}/display/{space_key}"),
                "description": config_space.get("description", ""),
                "status": config_space.get("status", "current")
            }
            all_spaces_to_process.append(main_space)
            
            # Get all nested spaces
            print(f"  🔍 Finding nested spaces...")
            nested_spaces = get_all_nested_spaces(client, space_key, max_depth=3)
            
            if nested_spaces:
                print(f"  📂 Found {len(nested_spaces)} nested spaces")
                for nested_space in nested_spaces:
                    print(f"    - {nested_space['name']} ({nested_space['key']}) - Depth: {nested_space['depth']}")
                all_spaces_to_process.extend(nested_spaces)
            else:
                print(f"  📂 No nested spaces found")
        
        print(f"\n📊 Total spaces to process: {len(all_spaces_to_process)}")
        
        # Process all spaces and their pages with smaller batches
        total_processed = 0
        space_batch_size = 2  # Process fewer spaces at a time
        page_limit = None  # No limit - get ALL pages
        
        for i in range(0, len(all_spaces_to_process), space_batch_size):
            space_batch = all_spaces_to_process[i:i + space_batch_size]
            print(f"\n🔄 Processing space batch {i//space_batch_size + 1}/{(len(all_spaces_to_process) + space_batch_size - 1)//space_batch_size}")
            
            for space in space_batch:
                try:
                    print(f"  📄 Processing space: {space['name']} ({space['key']}) - Depth: {space['depth']}")
                    
                    # Get pages from this space with limit (now including nested pages)
                    pages = get_all_pages_recursive(client, space["key"], limit=page_limit)
                    
                    if not pages:
                        print(f"    ⚠️ No pages found in {space['name']} ({space['key']})")
                        continue
                    
                    print(f"    📄 Found {len(pages)} pages in {space['name']} (including nested pages)")
                    
                    # Track this space as processed
                    processed_spaces.append({
                        "name": space["name"],
                        "key": space["key"],
                        "depth": space["depth"],
                        "page_count": len(pages)
                    })
                    
                    # Process pages in smaller batches
                    page_batch_size = 5
                    for j in range(0, len(pages), page_batch_size):
                        page_batch = pages[j:j + page_batch_size]
                        print(f"      🔄 Processing page batch {j//page_batch_size + 1}/{(len(pages) + page_batch_size - 1)//page_batch_size} for {space['name']}")
                        
                        docs_with_embeddings = []
                        
                        # Process each page (including PDF attachments)
                        for page in page_batch:
                            try:
                                print(f"        📄 Processing page: {page.get('title', 'Unknown')} (ID: {page.get('id', 'Unknown')})")
                                
                                # Get page content and PDF attachments
                                documents = client.get_page_with_attachments(page)
                                
                                for doc in documents:
                                    print(f"          📝 Processing document: {doc['title']} (Type: {doc.get('type', 'page')})")
                                    
                                    # Get embedding for the document content
                                    vector = get_embedding(doc["text"])
                                    if vector:
                                        # Prepare metadata
                                        metadata = {
                                            "page_id": doc["id"],
                                            "page_title": doc["title"],
                                            "space_key": space["key"],
                                            "space_name": space["name"],
                                            "space_depth": space["depth"],
                                            "parent_space": space.get("parent_key"),
                                            "url": doc["url"],
                                            "version": doc["version"],
                                            "content_type": doc.get("type", "page")
                                        }
                                        
                                        # Add PDF-specific metadata
                                        if doc.get("type") == "pdf_attachment":
                                            metadata.update({
                                                "attachment_id": doc.get("attachment_id"),
                                                "attachment_title": doc.get("attachment_title")
                                            })
                                            print(f"            📎 PDF attachment: {doc.get('attachment_title')}")
                                        
                                        docs_with_embeddings.append({
                                            "text": f"Space: {space['name']}\nTitle: {doc['title']}\n\n{doc['text']}",
                                            "vector": vector,
                                            "metadata": metadata
                                        })
                                        total_processed += 1
                                        print(f"            ✅ Added to batch: {doc['title']}")
                                    else:
                                        print(f"            ⚠️ Failed to get embedding for: {doc['title']} in {space['name']}")
                                        
                            except Exception as e:
                                print(f"        ❌ Error processing page {page.get('title', 'Unknown')} in {space['name']}: {e}")
                                continue
                        
                        # Upsert the page batch
                        if docs_with_embeddings:
                            try:
                                upsert_embeddings(docs_with_embeddings)
                                print(f"        ✅ Processed {len(docs_with_embeddings)} documents in this page batch for {space['name']}")
                            except Exception as e:
                                print(f"        ❌ Error upserting batch for {space['name']}: {e}")
                                # Continue with next batch instead of failing completely
                                continue
                    
                except Exception as e:
                    print(f"  ❌ Error processing space {space['name']} ({space['key']}): {e}")
                    continue
        
        print(f"\n🎉 Successfully ingested {total_processed} documents from configured spaces (including PDF attachments)")
        
        # Print summary of processed spaces
        print(f"\n📋 Summary of processed spaces:")
        for space in processed_spaces:
            print(f"  - {space['name']} ({space['key']}) - Depth: {space['depth']} - Pages: {space['page_count']}")
        
        return processed_spaces
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        raise

def ingest_from_confluence(space_key: str = None):
    """
    Ingest documents from Confluence into the vector database (legacy function).
    """
    try:
        print("🔗 Connecting to Confluence...")
        client = ConfluenceClient()
        
        print("📄 Fetching pages from Confluence...")
        pages = client.get_pages_for_ingestion(space_key=space_key)
        
        if not pages:
            print("⚠️ No pages found to ingest.")
            return
        
        print(f"📚 Found {len(pages)} pages to process")
        
        # Create collection if it doesn't exist
        create_collection()
        
        # Process pages in batches to avoid memory issues
        batch_size = 10
        total_processed = 0
        
        for i in range(0, len(pages), batch_size):
            batch = pages[i:i + batch_size]
            print(f"🔄 Processing batch {i//batch_size + 1}/{(len(pages) + batch_size - 1)//batch_size}")
            
            docs_with_embeddings = []
            for page in batch:
                try:
                    # Get embedding for the page content
                    vector = get_embedding(page["text"])
                    if vector:
                        docs_with_embeddings.append({
                            "text": f"Title: {page['title']}\n\n{page['text']}",
                            "vector": vector,
                            "metadata": {
                                "page_id": page["id"],
                                "title": page["title"],
                                "space_key": page["space_key"],
                                "url": page["url"],
                                "version": page["version"]
                            }
                        })
                        total_processed += 1
                    else:
                        print(f"⚠️ Failed to get embedding for page: {page['title']}")
                        
                except Exception as e:
                    print(f"❌ Error processing page {page['title']}: {e}")
                    continue
            
            # Upsert the batch
            if docs_with_embeddings:
                upsert_embeddings(docs_with_embeddings)
                print(f"✅ Processed {len(docs_with_embeddings)} pages in this batch")
        
        print(f"🎉 Successfully ingested {total_processed} pages from Confluence")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        raise

def ingest_from_local_docs():
    """
    Ingest documents from local docs folder (fallback option).
    """
    docs_folder = os.getenv("DOCS_FOLDER", "docs/")
    
    if not os.path.exists(docs_folder):
        print(f"⚠️ Docs folder '{docs_folder}' not found.")
        return
    
    docs = []
    for filename in os.listdir(docs_folder):
        if filename.endswith(".txt"):
            with open(os.path.join(docs_folder, filename), "r") as f:
                text = f.read()
                vector = get_embedding(text)
                if vector:
                    docs.append({"text": text, "vector": vector})
    
    if docs:
        create_collection()
        upsert_embeddings(docs)
        print(f"✅ Ingested {len(docs)} local documents into Qdrant")
    else:
        print("⚠️ No documents found to ingest.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "config":
            print("📋 Ingesting from configured spaces...")
            ingest_from_config()
        elif sys.argv[1] == "local":
            print("📁 Ingesting from local documents...")
            ingest_from_local_docs()
        else:
            print("🌐 Ingesting from Confluence...")
            space_key = sys.argv[1] if len(sys.argv) > 1 else None
            if space_key:
                print(f"📂 Using space key: {space_key}")
            ingest_from_confluence(space_key)
    else:
        print("📋 Ingesting from configured spaces...")
        ingest_from_config()
