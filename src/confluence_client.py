# src/confluence_client.py

import requests
import os
import base64
import tempfile
from typing import List, Dict, Any
from dotenv import load_dotenv
import PyPDF2
import io

# Load environment variables from .env file
load_dotenv()

class ConfluenceClient:
    def __init__(self):
        self.base_url = os.getenv("CONFLUENCE_BASE_URL")
        self.username = os.getenv("CONFLUENCE_USERNAME")
        self.api_token = os.getenv("CONFLUENCE_API_TOKEN")
        
        if not all([self.base_url, self.username, self.api_token]):
            raise ValueError("Missing Confluence environment variables. Please set CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, and CONFLUENCE_API_TOKEN")
        
        # Create Basic Auth header
        credentials = f"{self.username}:{self.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
    
    def get_all_pages(self, space_key: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all pages from Confluence, optionally filtered by space key.
        """
        pages = []
        start = 0
        
        # Use a reasonable default limit if None is provided
        if limit is None:
            limit = 1000  # Large number to get all pages
        
        while True:
            url = f"{self.base_url}/rest/api/content"
            params = {
                "type": "page",
                "limit": limit,
                "start": start,
                "expand": "body.storage,version,space"
            }
            
            if space_key:
                params["spaceKey"] = space_key
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                break
                
            pages.extend(results)
            
            # Check if there are more pages
            if not data.get("_links", {}).get("next"):
                break
                
            start += limit
        
        return pages
    
    def get_page_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Get all attachments for a specific page.
        """
        try:
            url = f"{self.base_url}/rest/api/content/{page_id}/child/attachment"
            params = {
                "limit": 100,
                "expand": "version"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("results", [])
            
        except Exception as e:
            print(f"Error getting attachments for page {page_id}: {e}")
            return []
    
    def download_attachment(self, attachment: Dict[str, Any]) -> bytes:
        """
        Download an attachment file.
        """
        try:
            download_url = attachment.get("_links", {}).get("download")
            if not download_url:
                return None
            
            # Make sure we have the full URL
            if download_url.startswith("/"):
                download_url = f"{self.base_url}{download_url}"
            
            response = requests.get(download_url, headers=self.headers)
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            print(f"Error downloading attachment {attachment.get('title')}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text content from a PDF file.
        """
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        Get detailed content of a specific page.
        """
        url = f"{self.base_url}/rest/api/content/{page_id}"
        params = {
            "expand": "body.storage,version,space"
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def search_pages(self, query: str, space_key: str = None) -> List[Dict[str, Any]]:
        """
        Search for pages using Confluence's search API.
        """
        url = f"{self.base_url}/rest/api/content/search"
        params = {
            "cql": f'text ~ "{query}"',
            "limit": 50,
            "expand": "body.storage,version,space"
        }
        
        if space_key:
            params["cql"] = f'space = "{space_key}" AND text ~ "{query}"'
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json().get("results", [])
    
    def extract_text_content(self, page: Dict[str, Any]) -> str:
        """
        Extract clean text content from a Confluence page.
        """
        try:
            # Get the storage content (HTML)
            storage_content = page.get("body", {}).get("storage", {}).get("value", "")
            
            # Clean HTML content using BeautifulSoup
            from bs4 import BeautifulSoup
            if storage_content:
                soup = BeautifulSoup(storage_content, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                # Get text and clean up whitespace
                text = soup.get_text()
                # Clean up extra whitespace and newlines
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                return text
            
            return ""
            
        except Exception as e:
            print(f"Error extracting content from page {page.get('id')}: {e}")
            return ""
    
    def get_page_with_attachments(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get a page and all its PDF attachments as separate documents.
        """
        documents = []
        
        # Add the main page content
        text_content = self.extract_text_content(page)
        if text_content.strip():
            # Handle cases where space field might be missing
            space_key = page.get("space", {}).get("key") if page.get("space") else "unknown"
            
            documents.append({
                "id": page["id"],
                "title": page["title"],
                "space_key": space_key,
                "text": text_content,
                "url": f"{self.base_url}/pages/viewpage.action?pageId={page['id']}",
                "version": page.get("version", {}).get("number", 1),
                "type": "page"
            })
        
        # Get and process attachments
        attachments = self.get_page_attachments(page["id"])
        for attachment in attachments:
            attachment_title = attachment.get("title", "")
            
            # Only process PDF attachments
            if attachment_title.lower().endswith('.pdf'):
                print(f"    📎 Processing PDF attachment: {attachment_title}")
                
                # Download the PDF
                pdf_content = self.download_attachment(attachment)
                if pdf_content:
                    # Extract text from PDF
                    pdf_text = self.extract_text_from_pdf(pdf_content)
                    if pdf_text.strip():
                        # Handle cases where space field might be missing
                        space_key = page.get("space", {}).get("key") if page.get("space") else "unknown"
                        
                        documents.append({
                            "id": f"{page['id']}_{attachment['id']}",
                            "title": f"{page['title']} - {attachment_title}",
                            "space_key": space_key,
                            "text": pdf_text,
                            "url": f"{self.base_url}/pages/viewpage.action?pageId={page['id']}",
                            "version": page.get("version", {}).get("number", 1),
                            "type": "pdf_attachment",
                            "attachment_id": attachment["id"],
                            "attachment_title": attachment_title
                        })
                        print(f"      ✅ Extracted {len(pdf_text)} characters from PDF")
                    else:
                        print(f"      ⚠️ No text extracted from PDF: {attachment_title}")
                else:
                    print(f"      ❌ Failed to download PDF: {attachment_title}")
        
        return documents
    
    def get_child_spaces(self, parent_space_key: str) -> List[Dict[str, Any]]:
        """
        Get child spaces of a parent space.
        """
        try:
            url = f"{self.base_url}/rest/api/space"
            params = {
                "limit": 100,
                "type": "global",
                "spaceKey": parent_space_key
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"Error getting child spaces for {parent_space_key}: {e}")
            return []

    def get_all_spaces(self) -> List[Dict[str, Any]]:
        """
        Get all spaces from Confluence.
        """
        spaces = []
        start = 0
        limit = 100
        
        while True:
            url = f"{self.base_url}/rest/api/space"
            params = {
                "limit": limit,
                "start": start,
                "expand": "description.plain"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                break
                
            spaces.extend(results)
            
            # Check if there are more spaces
            if not data.get("_links", {}).get("next"):
                break
                
            start += limit
        
        return spaces

    def get_pages_for_ingestion(self, space_key: str = None) -> List[Dict[str, Any]]:
        """
        Get all pages and format them for ingestion into the vector database.
        """
        pages = self.get_all_pages(space_key=space_key)
        
        formatted_pages = []
        for page in pages:
            text_content = self.extract_text_content(page)
            if text_content.strip():  # Only include pages with content
                formatted_pages.append({
                    "id": page["id"],
                    "title": page["title"],
                    "space_key": page["space"]["key"],
                    "text": text_content,
                    "url": f"{self.base_url}/pages/viewpage.action?pageId={page['id']}",
                    "version": page["version"]["number"]
                })
        
        return formatted_pages


def test_confluence_connection():
    """
    Test function to verify Confluence connection and get sample pages.
    """
    try:
        client = ConfluenceClient()
        print("✅ Successfully connected to Confluence")
        
        # Get first few pages as a test
        pages = client.get_all_pages(limit=5)
        print(f"📄 Found {len(pages)} pages")
        
        for page in pages[:3]:  # Show first 3 pages
            print(f"  - {page['title']} (ID: {page['id']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Confluence: {e}")
        return False


if __name__ == "__main__":
    test_confluence_connection() 