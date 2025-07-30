# src/ingest.py

import os
import json
import hashlib
import argparse
from datetime import datetime, timedelta
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

def load_progress():
    """
    Load ingestion progress from progress/ingestion_progress.json
    """
    progress_path = os.path.join("progress", "ingestion_progress.json")
    try:
        if os.path.exists(progress_path):
            with open(progress_path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading progress: {e}")
    return {
        "last_run": None,
        "processed_spaces": {},
        "processed_pages": {},
        "total_documents": 0,
        "last_updated": None,
        "current_progress": {
            "current_space_index": 0,
            "current_page_index": 0,
            "current_batch_index": 0,
            "total_spaces": 0,
            "total_pages": 0,
            "total_batches": 0,
            "percentage_complete": 0.0
        }
    }

def save_progress(progress_data):
    """
    Save ingestion progress to progress/ingestion_progress.json
    """
    os.makedirs("progress", exist_ok=True)
    progress_path = os.path.join("progress", "ingestion_progress.json")
    try:
        with open(progress_path, "w") as f:
            json.dump(progress_data, f, indent=2, default=str)
    except Exception as e:
        print(f"⚠️ Error saving progress: {e}")

def get_content_hash(content):
    """
    Generate a hash for content to detect changes
    """
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def is_content_updated(page_id, content_hash, progress_data):
    """
    Check if content has been updated since last ingestion
    """
    if page_id not in progress_data["processed_pages"]:
        return True  # New page
    
    last_hash = progress_data["processed_pages"][page_id].get("content_hash")
    return last_hash != content_hash

def update_progress(progress_data, space_key, page_id, content_hash, metadata):
    """
    Update progress tracking data
    """
    if space_key not in progress_data["processed_spaces"]:
        progress_data["processed_spaces"][space_key] = {
            "last_processed": datetime.now().isoformat(),
            "page_count": 0
        }
    
    progress_data["processed_spaces"][space_key]["page_count"] += 1
    progress_data["processed_spaces"][space_key]["last_processed"] = datetime.now().isoformat()
    
    progress_data["processed_pages"][page_id] = {
        "content_hash": content_hash,
        "last_processed": datetime.now().isoformat(),
        "metadata": metadata
    }
    
    progress_data["last_updated"] = datetime.now().isoformat()
    progress_data["total_documents"] += 1

def update_current_progress(progress_data, space_index, page_index, batch_index, total_spaces, total_pages, total_batches):
    """
    Update current progress tracking
    """
    if "current_progress" not in progress_data:
        progress_data["current_progress"] = {}
    
    progress_data["current_progress"].update({
        "current_space_index": space_index,
        "current_page_index": page_index,
        "current_batch_index": batch_index,
        "total_spaces": total_spaces,
        "total_pages": total_pages,
        "total_batches": total_batches
    })
    
    # Calculate percentage
    if total_spaces > 0 and total_pages > 0:
        space_progress = space_index / total_spaces
        page_progress = page_index / total_pages
        overall_progress = (space_progress + page_progress) / 2
        progress_data["current_progress"]["percentage_complete"] = round(overall_progress * 100, 2)

def print_progress_bar(current, total, prefix="Progress", suffix="Complete", length=50):
    """
    Print a progress bar
    """
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    percentage = current / total * 100
    print(f'\r{prefix}: |{bar}| {percentage:.1f}% {suffix}', end='', flush=True)
    if current == total:
        print()  # New line when complete

def print_detailed_progress(progress_data, current_space, current_page, total_spaces, total_pages, total_processed, total_updated, total_skipped):
    """
    Print detailed progress information
    """
    current_progress = progress_data.get("current_progress", {})
    percentage = current_progress.get("percentage_complete", 0.0)
    
    print(f"\n📊 Progress: {percentage:.1f}% Complete")
    print(f"   🌐 Space: {current_space} ({current_progress.get('current_space_index', 0) + 1}/{total_spaces})")
    print(f"   📄 Page: {current_page} ({current_progress.get('current_page_index', 0) + 1}/{total_pages})")
    print(f"   📝 Processed: {total_processed} | Updated: {total_updated} | Skipped: {total_skipped}")
    
    # Print progress bar
    if total_pages > 0:
        current_page_index = current_progress.get('current_page_index', 0)
        print_progress_bar(current_page_index, total_pages, "Page Progress", "Complete")

def get_resume_point(progress_data, all_spaces_to_process):
    """
    Determine where to resume from based on progress data
    """
    current_progress = progress_data.get("current_progress", {})
    
    # If no progress data, start from beginning
    if not current_progress.get("current_space_index"):
        return 0, 0, 0
    
    # Resume from last known position
    space_index = current_progress.get("current_space_index", 0)
    page_index = current_progress.get("current_page_index", 0)
    batch_index = current_progress.get("current_batch_index", 0)
    
    print(f"🔄 Resuming from: Space {space_index + 1}/{len(all_spaces_to_process)}, Page {page_index + 1}")
    
    return space_index, page_index, batch_index

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
    
    def get_children_recursive(parent_pages, level=1):
        if level > 3:  # Limit recursion depth
            return
        
        for parent_page in parent_pages:
            try:
                print(f"      🔍 Getting child pages for: {parent_page.get('title', 'Unknown')} (Level {level})")
                child_pages = get_child_pages(client, parent_page.get('id'))
                
                if child_pages:
                    print(f"      📄 Found {len(child_pages)} child pages for: {parent_page.get('title', 'Unknown')}")
                    all_pages.extend(child_pages)
                    get_children_recursive(child_pages, level + 1)
                else:
                    print(f"      📄 No child pages for: {parent_page.get('title', 'Unknown')}")
                    
            except Exception as e:
                print(f"      ❌ Error getting child pages for {parent_page.get('title', 'Unknown')}: {e}")
                continue
    
    # Get nested pages recursively
    get_children_recursive(top_level_pages)
    
    return all_pages

def ingest_from_config(incremental=False, daily=False, force=False, resume=True):
    """
    Ingest documents from configured spaces including all nested spaces and PDF attachments
    Supports incremental updates and progress tracking with resume capability
    """
    try:
        print("📋 Loading configuration...")
        config_spaces = load_config()
        
        if not config_spaces:
            print("❌ No spaces found in config file")
            return
        
        # Load progress data
        progress_data = load_progress()
        
        if incremental or daily:
            print("🔄 Running in incremental mode")
            if progress_data["last_run"]:
                last_run = datetime.fromisoformat(progress_data["last_run"])
                print(f"📅 Last run: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if daily:
                    # For daily runs, only process if last run was more than 24 hours ago
                    if datetime.now() - last_run < timedelta(hours=24):
                        print("⏰ Last run was less than 24 hours ago. Skipping daily update.")
                        return
        else:
            print("🔄 Running in full mode (will process all content)")
            if not force:
                print("⚠️ Use --force to confirm full ingestion")
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
        
        # Determine resume point
        if resume:
            start_space_index, start_page_index, start_batch_index = get_resume_point(progress_data, all_spaces_to_process)
        else:
            start_space_index, start_page_index, start_batch_index = 0, 0, 0
        
        # Process all spaces and their pages with smaller batches
        total_processed = 0
        total_updated = 0
        total_skipped = 0
        space_batch_size = 2  # Process fewer spaces at a time
        page_limit = None  # No limit - get ALL pages
        
        # Calculate total pages for progress tracking
        total_pages = 0
        for space in all_spaces_to_process:
            try:
                pages = get_all_pages_recursive(client, space["key"], limit=page_limit)
                total_pages += len(pages)
            except Exception as e:
                print(f"  ⚠️ Could not count pages for {space['name']}: {e}")
        
        print(f"📄 Total pages to process: {total_pages}")
        
        for i in range(start_space_index, len(all_spaces_to_process), space_batch_size):
            space_batch = all_spaces_to_process[i:i + space_batch_size]
            batch_num = i//space_batch_size + 1
            total_batches = (len(all_spaces_to_process) + space_batch_size - 1)//space_batch_size
            
            print(f"\n🔄 Processing space batch {batch_num}/{total_batches}")
            
            for space_idx, space in enumerate(space_batch):
                try:
                    current_space_name = space['name']
                    print(f"  📄 Processing space: {current_space_name} ({space['key']}) - Depth: {space['depth']}")
                    
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
                    for j in range(start_page_index if space_idx == 0 and i == start_space_index else 0, len(pages), page_batch_size):
                        page_batch = pages[j:j + page_batch_size]
                        batch_num = j//page_batch_size + 1
                        total_page_batches = (len(pages) + page_batch_size - 1)//page_batch_size
                        
                        print(f"      🔄 Processing page batch {batch_num}/{total_page_batches} for {space['name']}")
                        
                        docs_with_embeddings = []
                        
                        # Process each page (including PDF attachments)
                        for page_idx, page in enumerate(page_batch):
                            try:
                                page_id = page.get('id', 'Unknown')
                                page_title = page.get('title', 'Unknown')
                                
                                # Update progress tracking
                                current_page_index = j + page_idx
                                update_current_progress(progress_data, i, current_page_index, batch_num, 
                                                      len(all_spaces_to_process), total_pages, total_batches)
                                
                                print(f"        📄 Processing page: {page_title} (ID: {page_id})")
                                
                                # Get page content and PDF attachments
                                documents = client.get_page_with_attachments(page)
                                
                                for doc in documents:
                                    doc_id = f"{page_id}_{doc.get('type', 'page')}"
                                    content_hash = get_content_hash(doc["text"])
                                    
                                    # Check if content needs updating (incremental mode)
                                    if incremental and not is_content_updated(doc_id, content_hash, progress_data):
                                        print(f"          ⏭️ Skipping unchanged: {doc['title']}")
                                        total_skipped += 1
                                        continue
                                    
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
                                            "content_type": doc.get("type", "page"),
                                            "last_updated": datetime.now().isoformat()
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
                                        
                                        # Update progress tracking
                                        update_progress(progress_data, space["key"], doc_id, content_hash, metadata)
                                        
                                        total_processed += 1
                                        if incremental:
                                            total_updated += 1
                                            print(f"            ✅ Updated: {doc['title']}")
                                        else:
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
                                
                                # Print detailed progress
                                print_detailed_progress(progress_data, current_space_name, page_title, 
                                                      len(all_spaces_to_process), total_pages, 
                                                      total_processed, total_updated, total_skipped)
                                
                                # Save progress after each batch
                                save_progress(progress_data)
                                
                            except Exception as e:
                                print(f"        ❌ Error upserting batch for {space['name']}: {e}")
                                # Continue with next batch instead of failing completely
                                continue
                    
                    # Reset page index for next space
                    start_page_index = 0
                    
                except Exception as e:
                    print(f"  ❌ Error processing space {space['name']} ({space['key']}): {e}")
                    continue
        
        # Save final progress data
        progress_data["last_run"] = datetime.now().isoformat()
        save_progress(progress_data)
        
        # Print final summary
        if incremental:
            print(f"\n🎉 Incremental ingestion completed!")
            print(f"📊 Final Summary:")
            print(f"  - Total documents processed: {total_processed}")
            print(f"  - Documents updated: {total_updated}")
            print(f"  - Documents skipped (unchanged): {total_skipped}")
            print(f"  - Final progress: 100% Complete")
        else:
            print(f"\n🎉 Successfully ingested {total_processed} documents from configured spaces (including PDF attachments)")
            print(f"📊 Final progress: 100% Complete")
        
        # Print summary of processed spaces
        print(f"\n📋 Summary of processed spaces:")
        for space in processed_spaces:
            print(f"  - {space['name']} ({space['key']}) - Depth: {space['depth']} - Pages: {space['page_count']}")
        
        return processed_spaces
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        print(f"💾 Progress saved - you can resume from where it stopped")
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
            print("❌ No pages found")
            return
        
        print(f"📄 Found {len(pages)} pages")
        
        # Create collection if it doesn't exist
        create_collection()
        
        # Process pages in batches
        batch_size = 5
        total_processed = 0
        
        for i in range(0, len(pages), batch_size):
            batch = pages[i:i + batch_size]
            print(f"🔄 Processing batch {i//batch_size + 1}/{(len(pages) + batch_size - 1)//batch_size}")
            
            docs_with_embeddings = []
            
            for page in batch:
                try:
                    print(f"  📄 Processing page: {page.get('title', 'Unknown')}")
                    
                    # Get page content
                    content = client.get_page_content(page.get('id'))
                    if not content:
                        print(f"    ⚠️ No content found for page: {page.get('title', 'Unknown')}")
                        continue
                    
                    # Get embedding for the page content
                    vector = get_embedding(content)
                    if vector:
                        docs_with_embeddings.append({
                            "text": content,
                            "vector": vector,
                            "metadata": {
                                "page_id": page.get('id'),
                                "page_title": page.get('title'),
                                "space_key": page.get('space', {}).get('key'),
                                "url": page.get('_links', {}).get('webui', ''),
                                "version": page.get('version', {}).get('number', 1)
                            }
                        })
                        total_processed += 1
                        print(f"    ✅ Added to batch: {page.get('title', 'Unknown')}")
                    else:
                        print(f"    ⚠️ Failed to get embedding for: {page.get('title', 'Unknown')}")
                        
                except Exception as e:
                    print(f"    ❌ Error processing page {page.get('title', 'Unknown')}: {e}")
                    continue
            
            # Upsert the batch
            if docs_with_embeddings:
                try:
                    upsert_embeddings(docs_with_embeddings)
                    print(f"  ✅ Processed {len(docs_with_embeddings)} documents in this batch")
                except Exception as e:
                    print(f"  ❌ Error upserting batch: {e}")
                    continue
        
        print(f"\n🎉 Successfully ingested {total_processed} documents from Confluence")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        raise

def ingest_from_local_docs():
    """
    Ingest documents from local docs folder
    """
    try:
        print("📁 Loading documents from local docs folder...")
        
        docs_folder = "docs"
        if not os.path.exists(docs_folder):
            print(f"❌ Docs folder '{docs_folder}' not found")
            return
        
        # Create collection if it doesn't exist
        create_collection()
        
        # Get all files in docs folder
        files = []
        for root, dirs, filenames in os.walk(docs_folder):
            for filename in filenames:
                if filename.endswith(('.txt', '.md', '.pdf')):
                    filepath = os.path.join(root, filename)
                    files.append(filepath)
        
        if not files:
            print("❌ No supported files found in docs folder")
            return
        
        print(f"📄 Found {len(files)} files to process")
        
        # Process files in batches
        batch_size = 5
        total_processed = 0
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            print(f"🔄 Processing batch {i//batch_size + 1}/{(len(files) + batch_size - 1)//batch_size}")
            
            docs_with_embeddings = []
            
            for filepath in batch:
                try:
                    filename = os.path.basename(filepath)
                    print(f"  📄 Processing file: {filename}")
                    
                    # Read file content
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if not content.strip():
                        print(f"    ⚠️ Empty file: {filename}")
                        continue
                    
                    # Get embedding for the file content
                    vector = get_embedding(content)
                    if vector:
                        docs_with_embeddings.append({
                            "text": content,
                            "vector": vector,
                            "metadata": {
                                "filename": filename,
                                "filepath": filepath,
                                "file_type": os.path.splitext(filename)[1],
                                "file_size": len(content)
                            }
                        })
                        total_processed += 1
                        print(f"    ✅ Added to batch: {filename}")
                    else:
                        print(f"    ⚠️ Failed to get embedding for: {filename}")
                        
                except Exception as e:
                    print(f"    ❌ Error processing file {filename}: {e}")
                    continue
            
            # Upsert the batch
            if docs_with_embeddings:
                try:
                    upsert_embeddings(docs_with_embeddings)
                    print(f"  ✅ Processed {len(docs_with_embeddings)} documents in this batch")
                except Exception as e:
                    print(f"  ❌ Error upserting batch: {e}")
                    continue
        
        print(f"\n🎉 Successfully ingested {total_processed} documents from local docs folder")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    parser = argparse.ArgumentParser(description="Ingest documents from Confluence or local files.")
    parser.add_argument("--incremental", action="store_true", help="Run ingestion in incremental mode (skips unchanged documents).")
    parser.add_argument("--daily", action="store_true", help="Run ingestion in daily mode (only processes if last run was more than 24 hours ago).")
    parser.add_argument("--force", action="store_true", help="Force full ingestion even if incremental/daily mode is active.")
    parser.add_argument("--no-resume", action="store_true", help="Don't resume from previous progress.")
    parser.add_argument("--config", action="store_true", help="Ingest from configured spaces (default).")
    parser.add_argument("--local", action="store_true", help="Ingest from local documents.")
    parser.add_argument("--confluence", nargs="?", const="all", help="Ingest from Confluence. Optionally specify a space key (e.g., 'MYSPACE').")
    
    args = parser.parse_args()
    
    if args.config:
        print("📋 Ingesting from configured spaces...")
        ingest_from_config(incremental=args.incremental, daily=args.daily, force=args.force, resume=not args.no_resume)
    elif args.local:
        print("📁 Ingesting from local documents...")
        ingest_from_local_docs()
    elif args.confluence:
        print("🌐 Ingesting from Confluence...")
        space_key = args.confluence if args.confluence != "all" else None
        if space_key:
            print(f"📂 Using space key: {space_key}")
        ingest_from_confluence(space_key)
    else:
        print("📋 Ingesting from configured spaces...")
        ingest_from_config(incremental=args.incremental, daily=args.daily, force=args.force, resume=not args.no_resume)
