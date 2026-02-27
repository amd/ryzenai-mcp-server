#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright(C) 2026 Advanced Micro Devices, Inc. All rights reserved.
"""
Enhanced MCP server with Tree-sitter AST chunking for "Chat with Repo" functionality
Combines documentation and code files with smart chunking strategies
"""

import sys
import io

# Fix Windows encoding issues - force UTF-8 for stdout/stderr
if sys.platform == 'win32':
    # Reconfigure stdout and stderr to use UTF-8 encoding
    if hasattr(sys.stdout, 'buffer'):
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    if hasattr(sys.stderr, 'buffer'):
        if sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse, quote
import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
import re
import json
import os
import sqlite3
import hashlib
import threading
import time
from pathlib import Path

# Try to import embedding libraries
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Warning-transformers not available. Install with install sentence-transformers")

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("Warning not available. Install with install chromadb")

# Import hybrid chunker (fallback for when LangChain Tree-sitter is not available)
try:
    from hybrid_chunker import HybridChunker
    HYBRID_CHUNKING_AVAILABLE = True
except ImportError:
    HYBRID_CHUNKING_AVAILABLE = False
    print("Warning chunking not available. Install tree-sitter and run setup_tree_sitter.sh")

# Import enhanced LangChain Tree-sitter chunker
try:
    from ast_chunker_langchain import LangChainASTChunker
    LANGCHAIN_TREE_SITTER_AVAILABLE = True
except ImportError:
    LANGCHAIN_TREE_SITTER_AVAILABLE = False
    print("Warning Tree-sitter chunker not available. Install with install langchain-community tree-sitter-languages")

DOCS_BASE = "https://ryzenai.docs.amd.com"
GITHUB_REPO = "amd/RyzenAI-SW"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/" + GITHUB_REPO
GITHUB_API_SEARCH = "https://api.github.com/search/code"
GITHUB_API_CONTENTS = "https://api.github.com/repos/" + GITHUB_REPO + "/contents"

mcp = FastMCP("enhanced-ryzenai-mcp")

class EnhancedGitHubEmbeddingStore:
    def __init__(self, repo_path="./ryzenai_embeddings"):
        self.repo_path = Path(repo_path)
        self.repo_path.mkdir(exist_ok=True)
        
        # Initialize embedding model
        if EMBEDDINGS_AVAILABLE:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.model = None
            
        # Initialize vector database
        if CHROMA_AVAILABLE:
            self.chroma_client = chromadb.PersistentClient(path=str(self.repo_path / "chroma_db"))
            self.collection = self.chroma_client.get_or_create_collection(
                name="ryzenai_docs",
                metadata={"description": "AMD Ryzen AI documentation and code embeddings"}
            )
        else:
            self.chroma_client = None
            self.collection = None
            
        # Initialize chunkers with priority > Hybrid > None
        if LANGCHAIN_TREE_SITTER_AVAILABLE:
            self.enhanced_chunker = LangChainASTChunker()
            self.hybrid_chunker = None
            print("Using enhanced LangChain Tree-sitter chunker")
        elif HYBRID_CHUNKING_AVAILABLE:
            self.enhanced_chunker = None
            self.hybrid_chunker = HybridChunker()
            print("OK Using hybrid Tree-sitter chunker")
        else:
            self.enhanced_chunker = None
            self.hybrid_chunker = None
            print("WARNING  No AST chunking available, using simple text chunking")
            
        # SQLite for metadata
        self.db_path = self.repo_path / "metadata.db"
        self.init_sqlite()
        
    def init_sqlite(self):
        """Initialize SQLite database for metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE,
                content TEXT,
                file_type TEXT,
                chunking_method TEXT,
                last_modified REAL,
                content_hash TEXT,
                embedding_generated BOOLEAN DEFAULT FALSE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refresh_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_refresh_real REAL
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_file_hash(self, content):
        """Generate hash for file content"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_file_updated(self, path, content_hash):
        """Check if file needs updating"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT content_hash FROM files WHERE path = ?', (path,))
        result = cursor.fetchone()
        conn.close()
        
        if result is None:
            return True  # New file
        return result[0] != content_hash
    
    def save_file_metadata(self, path, content, file_type, chunking_method, content_hash):
        """Save file metadata to SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO files (path, content, file_type, chunking_method, last_modified, content_hash, embedding_generated)
            VALUES (?, ?, ?, ?, ?, ?, FALSE)
        ''', (path, content, file_type, chunking_method, time.time(), content_hash))
        conn.commit()
        conn.close()
    
    def mark_embedding_generated(self, path):
        """Mark that embedding has been generated for this file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE files SET embedding_generated = TRUE WHERE path = ?', (path,))
        conn.commit()
        conn.close()
    
    def get_files_needing_embeddings(self):
        """Get files that need embeddings generated"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT path, content, file_type, chunking_method FROM files WHERE embedding_generated = FALSE')
        results = cursor.fetchall()
        conn.close()
        
        return [{"path": row[0], "content": row[1], "file_type": row[2], "chunking_method": row[3]} for row in results]
    
    def get_last_refresh_time(self) -> Optional[float]:
        """Return Unix timestamp of last refresh, or None if never refreshed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT last_refresh_real FROM refresh_state WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] is not None else None

    def set_last_refresh_time(self, when: Optional[float] = None):
        """Record that a refresh completed at the given time (default: now)."""
        when = when if when is not None else time.time()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO refresh_state (id, last_refresh_real) VALUES (1, ?)',
            (when,)
        )
        conn.commit()
        conn.close()

    def clear_index(self):
        """Clear the vector DB and file metadata so the index can be rebuilt from scratch (e.g. after repo/docs update)."""
        if CHROMA_AVAILABLE and self.chroma_client:
            try:
                self.chroma_client.delete_collection("ryzenai_docs")
            except Exception:
                pass
            self.collection = self.chroma_client.get_or_create_collection(
                name="ryzenai_docs",
                metadata={"description": "AMD Ryzen AI documentation and code embeddings"}
            )
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM files')
        conn.commit()
        conn.close()
    
    def download_github_file(self, path):
        """Download a single file from GitHub"""
        try:
            url = f"{GITHUB_RAW_BASE}/HEAD/{path}"
            with httpx.Client(timeout=30) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error downloading {path}: {e}")
            return None
    
    def get_github_directory_contents(self, path = "", token = None):
        """Get directory contents from GitHub API"""
        url = f"{GITHUB_API_CONTENTS}/{path}" if path else GITHUB_API_CONTENTS
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            with httpx.Client(timeout=30, headers=headers) as client:
                r = client.get(url, params={"ref": "HEAD"})
                if r.status_code == 404:
                    return []
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"Error getting directory contents for {path}: {e}")
            return []
    
    def should_process_file(self, filename, path):
        """Determine if file should be processed"""
        # Process text files, code files, and documentation
        text_extensions = {'.py', '.pyi', '.cpp', '.cc', '.cxx', '.c++', '.hpp', '.hxx', '.c', '.h', '.md', '.txt', '.rst', '.json', '.yml', '.yaml', '.cfg', '.ini'}
        important_files = {'readme', 'tutorial', 'example', 'demo', 'getting_started'}
        
        # Check extension
        if any(filename.lower().endswith(ext) for ext in text_extensions):
            return True
            
        # Check if it's an important file
        if any(important in filename.lower() for important in important_files):
            return True
            
        # Check path for important directories
        if any(important in path.lower() for important in ['tutorial', 'example', 'demo', 'getting_started']):
            return True
            
        return False
    
    def get_file_type_and_chunking_method(self, file_path):
        """Determine file type and appropriate chunking method"""
        ext = file_path.split('.')[-1].lower()
        
        # Code files - use AST chunking
        code_extensions = {'.py', '.pyi', '.cpp', '.cc', '.cxx', '.c++', '.hpp', '.hxx', '.c', '.h'}
        if ext in code_extensions:
            return 'code', 'ast_tree_sitter'
        
        # Documentation files - use text chunking
        doc_extensions = {'.md', '.txt', '.rst', '.yml', '.yaml', '.json', '.cfg', '.ini'}
        if ext in doc_extensions:
            return 'documentation', 'langchain_text'
        
        # Default to text chunking
        return 'text', 'simple_text'
    
    def download_repository(self, max_files = 500, token = None):
        """Download repository files and store metadata with smart chunking"""
        print("Starting enhanced repository download with smart chunking...")
        
        def download_recursive(path = "", depth = 0, files_processed = 0):
            if depth > 3 or files_processed >= max_files:
                return files_processed
                
            contents = self.get_github_directory_contents(path, token)
            
            for item in contents:
                if files_processed >= max_files:
                    break
                    
                if item.get("type") == "file":
                    file_path = item.get("path", "")
                    filename = item.get("name", "")
                    
                    if self.should_process_file(filename, file_path):
                        content = self.download_github_file(file_path)
                        if content and len(content) > 50:
                            content_hash = self.get_file_hash(content)
                            
                            if self.is_file_updated(file_path, content_hash):
                                print(f"Processing: {file_path}")
                                
                                # Determine file type and chunking method
                                file_type, chunking_method = self.get_file_type_and_chunking_method(file_path)
                                
                                # Save metadata
                                self.save_file_metadata(file_path, content, file_type, chunking_method, content_hash)
                                files_processed += 1
                
                elif item.get("type") == "dir" and depth < 3:
                    files_processed = download_recursive(item.get("path", ""), depth + 1, files_processed)
            
            return files_processed
        
        total_files = download_recursive("", 0, 0)
        print(f"Downloaded {total_files} files")
        return total_files
    
    def generate_embeddings(self, batch_size = 10):
        """Generate embeddings using smart chunking strategies"""
        if not EMBEDDINGS_AVAILABLE or not CHROMA_AVAILABLE:
            print("Embedding libraries not available. Cannot generate embeddings.")
            return 0
        
        files_to_process = self.get_files_needing_embeddings()
        print(f"Generating embeddings for {len(files_to_process)} files with smart chunking...")
        
        processed = 0
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i:i + batch_size]
            
            # Process each file with appropriate chunking
            all_documents = []
            
            for file_info in batch:
                path = file_info["path"]
                content = file_info["content"]
                file_type = file_info["file_type"]
                chunking_method = file_info["chunking_method"]
                
                print(f"  Chunking {path} using {chunking_method}...")
                
                # Use appropriate chunking strategy with priority > Hybrid > Simple
                if chunking_method == 'ast_tree_sitter' and self.enhanced_chunker:
                    # Use enhanced LangChain Tree-sitter chunking for code files
                    documents = self.enhanced_chunker.chunk_file(path)
                elif chunking_method == 'ast_tree_sitter' and self.hybrid_chunker:
                    # Use hybrid Tree-sitter chunking for code files
                    documents = self.hybrid_chunker.chunk_file(content, path)
                else:
                    # Use simple chunking as fallback
                    documents = [{
                        "content": content[:8000] + "..." if len(content) > 8000 else content,
                        "metadata": {
                            "path": path,
                            "file_type": file_type,
                            "chunking_method": chunking_method,
                            "source": f"https://github.com/{GITHUB_REPO}/blob/HEAD/{path}"
                        }
                    }]
                
                all_documents.extend(documents)
            
            # Generate embeddings for all documents
            if all_documents:
                try:
                    # Prepare content for embedding
                    texts = []
                    metadatas = []
                    ids = []
                    
                    for doc in all_documents:
                        content = doc["content"]
                        metadata = doc["metadata"]
                        
                        # Truncate if too long
                        if len(content) > 8000:
                            content = content[:8000] + "..."
                        
                        texts.append(content)
                        metadatas.append(metadata)
                        ids.append(f"{metadata['path']}_{len(ids)}")
                    
                    # Generate embeddings
                    embeddings = self.model.encode(texts)
                    
                    # Store in ChromaDB
                    self.collection.add(
                        embeddings=embeddings.tolist(),
                        documents=texts,
                        metadatas=metadatas,
                        ids=ids
                    )
                    
                    # Mark files as processed
                    for file_info in batch:
                        self.mark_embedding_generated(file_info["path"])
                    
                    processed += len(batch)
                    print(f"Processed {processed}/{len(files_to_process)} files")
                    
                except Exception as e:
                    print(f"Error processing batch: {e}")
                    continue
        
        print(f"Generated embeddings for {processed} files")
        return processed
    
    def semantic_search(self, query, n_results = 10):
        """Perform semantic search using embeddings"""
        if not EMBEDDINGS_AVAILABLE or not CHROMA_AVAILABLE:
            print("Embedding libraries not available. Cannot perform semantic search.")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query])
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    formatted_results.append({
                        "path": metadata["path"],
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "score": 1 - distance,
                        "search_method": "enhanced_semantic",
                        "file_type": metadata.get("file_type", "unknown"),
                        "chunking_method": metadata.get("chunking_method", "unknown"),
                        "html_url": f"https://github.com/{GITHUB_REPO}/blob/HEAD/{metadata['path']}"
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []

# Global embedding store instance
enhanced_store = None
_refresh_thread_started = False

def _run_background_refresh_loop(store: EnhancedGitHubEmbeddingStore):
    """Daemon thread: refresh index every RYZENAI_INDEX_REFRESH_HOURS (default 24). Set to 0 to disable."""
    refresh_hours = float(os.environ.get("RYZENAI_INDEX_REFRESH_HOURS", "24"))
    if refresh_hours <= 0:
        return
    interval_sec = refresh_hours * 3600
    max_files = int(os.environ.get("RYZENAI_INDEX_MAX_FILES", "500"))
    token = os.environ.get("GITHUB_TOKEN")
    while True:
        try:
            last = store.get_last_refresh_time()
            now = time.time()
            if last is None:
                store.set_last_refresh_time(now)
                time.sleep(interval_sec)
                continue
            wait = (last + interval_sec) - now
            if wait > 0:
                time.sleep(wait)
            if not EMBEDDINGS_AVAILABLE or not CHROMA_AVAILABLE:
                break
            store.clear_index()
            store.download_repository(max_files=max_files, token=token)
            store.generate_embeddings()
            store.set_last_refresh_time(time.time())
        except Exception as e:
            print(f"Background index refresh error: {e}", file=sys.stderr)
            time.sleep(3600)

def get_enhanced_store():
    global enhanced_store, _refresh_thread_started
    if enhanced_store is None:
        enhanced_store = EnhancedGitHubEmbeddingStore()
        if not _refresh_thread_started and EMBEDDINGS_AVAILABLE and CHROMA_AVAILABLE:
            refresh_hours = float(os.environ.get("RYZENAI_INDEX_REFRESH_HOURS", "24"))
            if refresh_hours > 0:
                t = threading.Thread(target=_run_background_refresh_loop, args=(enhanced_store,), daemon=True)
                t.start()
                _refresh_thread_started = True
    return enhanced_store

# GitHub code search functions (from original server)
def _github_code_search(query, max_results = 5, token = None):
    """Original GitHub code search functionality"""
    q = f"repo:{GITHUB_REPO} {query}".strip()
    headers = {"Accept": "application/vnd.github.text-match+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=30, headers=headers) as client:
        try:
            r = client.get(GITHUB_API_SEARCH, params={"q": q, "per_page": min(max_results, 10)})
            r.raise_for_status()
            data = r.json()
        except Exception:
            return []
    
    items = data.get("items", [])
    out = []
    for it in items:
        out.append({
            "name": it.get("name"),
            "path": it.get("path"),
            "html_url": it.get("html_url"),
            "repository": it.get("repository", {}).get("full_name"),
            "score": it.get("score"),
            "search_method": "github_keyword"
        })
    return out

def _normalize_docs_url(path_or_url):
    url = urljoin(DOCS_BASE + "/", path_or_url)
    p = urlparse(url)
    if p.scheme != "https" or p.netloc != "ryzenai.docs.amd.com":
        raise ValueError(f"Only {DOCS_BASE} is allowed")
    return url

def _extract_main_text(html):
    soup = BeautifulSoup(html, "html.parser")
    main = (
        soup.select_one('[role="main"]')
        or soup.select_one("#main-content")
        or soup.select_one("main")
        or soup.body
    )
    text = (main.get_text(separator="\n") if main else soup.get_text(separator="\n")).strip()
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join([ln for ln in lines if ln])
    return text

def _github_read_raw(path, ref = "HEAD"):
    url = f"{GITHUB_RAW_BASE}/{quote(ref)}/{path.lstrip('/')}"
    with httpx.Client(timeout=30) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text

def _chunk(text, max_chars):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)] if text else []

# MCP Tools
@mcp.tool(
    name="read_ryzenai",
    description="Read and extract text from a Ryzen AI docs page (domain-limited)."
)
def read_ryzenai(path_or_url, max_chars = "6000"):
    # Convert max_chars to int (FastMCP may pass it as string)
    max_chars = int(max_chars)
    
    url = _normalize_docs_url(path_or_url)
    with httpx.Client(timeout=30) as client:
        r = client.get(url)
        r.raise_for_status()
        text = _extract_main_text(r.text)
    chunks = _chunk(text, max_chars)
    if chunks:
        chunks[0] = f"Source: {url}\n\n{chunks[0]}"
    return chunks

@mcp.tool(
    name="download_and_index_ryzenai_enhanced",
    description="Download AMD RyzenAI repository and create enhanced embeddings with smart chunking (LangChain Tree-sitter for code, text for docs)."
)
def download_and_index_ryzenai_enhanced(max_files = "300", github_token = None):
    """
    Download the AMD RyzenAI repository and create enhanced embeddings with smart chunking.
    
    Args:
      max_files number of files to download and index
      github_token GitHub token for higher rate limits
    
    Returns:
      Dictionary with download and indexing results
    """
    # Convert max_files to int (FastMCP may pass it as string)
    max_files = int(max_files)
    store = get_enhanced_store()
    
    # Check if embedding libraries are available
    if not EMBEDDINGS_AVAILABLE:
        return {
            "success": False,
            "error": "sentence-transformers not available. Install with: pip install sentence-transformers",
            "files_downloaded": 0,
            "embeddings_generated": 0
        }
    
    if not CHROMA_AVAILABLE:
        return {
            "success": False,
            "error": "chromadb not available. Install with: pip install chromadb",
            "files_downloaded": 0,
            "embeddings_generated": 0
        }
    
    try:
        # Download repository
        files_downloaded = store.download_repository(max_files, github_token)
        
        # Generate embeddings with smart chunking
        embeddings_generated = store.generate_embeddings()
        store.set_last_refresh_time()

        return {
            "success": True,
            "files_downloaded": files_downloaded,
            "embeddings_generated": embeddings_generated,
            "message": f"Successfully indexed {files_downloaded} files with {embeddings_generated} embeddings using smart chunking"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "files_downloaded": 0,
            "embeddings_generated": 0
        }

@mcp.tool(
    name="search_ryzenai_sw_enhanced",
    description="Enhanced semantic search of AMD RyzenAI repository using smart chunking (LangChain Tree-sitter for code, text for docs)."
)
def search_ryzenai_sw_enhanced(query, max_results = "10", github_token = None):
    """
    Enhanced search that combines semantic embeddings with smart chunking for comprehensive results.
    
    Args:
      query language query (e.g., 'ResNet BF16 inference', 'NPU optimization')
      max_results of results to return
      github_token GitHub token
    
    Returns:
      List of relevant files with semantic similarity scores
    """
    # Convert max_results to int (FastMCP may pass it as string)
    max_results = int(max_results)
    
    all_results = []
    
    # Strategy 1 enhanced semantic search first
    store = get_enhanced_store()
    semantic_results = store.semantic_search(query, max_results//2)
    all_results.extend(semantic_results)
    
    # Strategy 2 to keyword search
    keyword_results = _github_code_search(query, max_results//2, github_token)
    all_results.extend(keyword_results)
    
    # Strategy 3 no semantic results, try to download and index
    if not semantic_results:
        print("No embeddings found. Attempting to download and index repository with smart chunking...")
        index_result = download_and_index_ryzenai_enhanced(50, github_token)
        
        if index_result["success"]:
            # Try semantic search again
            semantic_results = store.semantic_search(query, max_results//2)
            all_results.extend(semantic_results)
        else:
            print(f"Failed to create embeddings: {index_result.get('error', 'Unknown error')}")
    
    # Remove duplicates and sort by score
    seen_paths = set()
    unique_results = []
    
    for result in all_results:
        path = result.get("path", "")
        if path not in seen_paths and len(unique_results) < max_results:
            seen_paths.add(path)
            unique_results.append(result)
    
    # Sort by score (semantic results typically have higher scores)
    unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return unique_results

@mcp.tool(
    name="search_ryzenai_sw_keyword",
    description="Search the amd/RyzenAI-SW GitHub repo using keyword search (original method)."
)
def search_ryzenai_sw_keyword(query, max_results = "5", github_token = None):
    """Original GitHub keyword search for amd/RyzenAI-SW repository."""
    # Convert max_results to int (FastMCP may pass it as string)
    return _github_code_search(query, int(max_results), github_token)

@mcp.tool(
    name="read_ryzenai_sw",
    description="Read a raw file from amd/RyzenAI-SW (examples/tutorials). Now handles directories gracefully."
)
def read_ryzenai_sw(path, ref = "HEAD", max_chars = "6000"):
    """
    Read a file from the AMD RyzenAI-SW repository with enhanced directory handling.
    
    Args:
        path path in the repository
        ref reference (default)
        max_chars characters per chunk
    
    Returns:
        List of text chunks with source information
    """
    # Convert max_chars to int (FastMCP may pass it as string)
    max_chars = int(max_chars)
    
    try:
        # First, try to read the file directly
        text = _github_read_raw(path=path, ref=ref)
        chunks = _chunk(text, max_chars)
        if chunks:
            chunks[0] = f"Source://github.com/{GITHUB_REPO}/blob/{ref}/{path}\n\n{chunks[0]}"
        return chunks
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Check if this might be a directory
            if not path.endswith(('.py', '.md', '.txt', '.json', '.yml', '.yaml', '.cpp', '.h', '.c', '.hpp')):
                # Try to read README.md in the directory
                readme_path = f"{path.rstrip('/')}/README.md"
                try:
                    text = _github_read_raw(path=readme_path, ref=ref)
                    chunks = _chunk(text, max_chars)
                    if chunks:
                        chunks[0] = f"Source://github.com/{GITHUB_REPO}/blob/{ref}/{readme_path}\n\n{chunks[0]}"
                    return chunks
                except httpx.HTTPStatusError:
                    pass
            
            # If still 404, provide helpful suggestions
            suggestions = []
            if not path.endswith('.md'):
                suggestions.append(f"Try: {path}/README.md")
            if not path.endswith('.py'):
                suggestions.append(f"Try: {path}.py")
            if not path.endswith('.json'):
                suggestions.append(f"Try: {path}.json")
            
            return [f"ERROR File not found: {path}\n\nTIP Suggestions:\n" + "\n".join(f"  • {s}" for s in suggestions) + f"\n\nSEARCH Use list_ryzenai_sw_directory('{path}') to see available files in this directory."]
        else:
            raise

@mcp.tool(
    name="list_ryzenai_sw_directory",
    description="List contents of a directory in the AMD RyzenAI-SW repository."
)
def list_ryzenai_sw_directory(path = "", ref = "HEAD", github_token = None):
    """
    List directory contents from the AMD RyzenAI-SW repository.
    
    Args:
        path path in the repository (empty for root)
        ref reference (default)
        github_token GitHub token for higher rate limits
    
    Returns:
        List of directory contents with file information
    """
    store = get_enhanced_store()
    contents = store.get_github_directory_contents(path, github_token)
    
    if not contents:
        return [{"error": f"Directory not found: {path}", "suggestions": ["Check if the path exists", "Try with an empty path for root directory"]}]
    
    # Format the results
    formatted_contents = []
    for item in contents:
        item_type = item.get("type", "unknown")
        name = item.get("name", "")
        item_path = item.get("path", "")
        size = item.get("size", 0)
        
        # Add helpful information based on type
        if item_type == "file":
            file_ext = name.split('.')[-1].lower() if '.' in name else ""
            description = f"File ({file_ext}) - {size} bytes"
            if file_ext in ['py', 'cpp', 'c', 'h', 'hpp']:
                description += " - Code file"
            elif file_ext in ['md', 'txt', 'rst']:
                description += " - Documentation"
            elif file_ext in ['json', 'yml', 'yaml']:
                description += " - Configuration"
        else:
            description = "Directory"
        
        formatted_contents.append({
            "name": name,
            "path": item_path,
            "type": item_type,
            "description": description,
            "size": size,
            "html_url": f"https://github.com/{GITHUB_REPO}/tree/{ref}/{item_path}" if item_type == "dir" else f"https://github.com/{GITHUB_REPO}/blob/{ref}/{item_path}"
        })
    
    # Sort first, then files
    formatted_contents.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
    
    return formatted_contents

@mcp.tool(
    name="find_ryzenai_sw_files",
    description="Find files in the AMD RyzenAI-SW repository by name pattern or type."
)
def find_ryzenai_sw_files(pattern = "", file_type = "", ref = "HEAD", github_token = None):
    """
    Find files in the AMD RyzenAI-SW repository by pattern or type.
    
    Args:
        pattern name pattern to search for (e.g., "resnet", "inference")
        file_type type filter (e.g., "py", "md", "json")
        ref reference (default)
        github_token GitHub token for higher rate limits
    
    Returns:
        List of matching files with information
    """
    store = get_enhanced_store()
    
    def search_recursive(path = "", depth = 0, max_depth = 3) -> List[Dict[str, Any]]:
        if depth > max_depth:
            return []
            
        contents = store.get_github_directory_contents(path, github_token)
        matches = []
        
        for item in contents:
            item_type = item.get("type", "unknown")
            name = item.get("name", "")
            item_path = item.get("path", "")
            
            if item_type == "file":
                # Check pattern match
                pattern_match = not pattern or pattern.lower() in name.lower()
                
                # Check file type match
                file_ext = name.split('.')[-1].lower() if '.' in name else ""
                type_match = not file_type or file_ext == file_type.lower()
                
                if pattern_match and type_match:
                    matches.append({
                        "name": name,
                        "path": item_path,
                        "type": "file",
                        "extension": file_ext,
                        "size": item.get("size", 0),
                        "html_url": f"https://github.com/{GITHUB_REPO}/blob/{ref}/{item_path}",
                        "description": f"File matching pattern '{pattern}'" if pattern else f"File of type '{file_ext}'"
                    })
            
            elif item_type == "dir" and depth < max_depth:
                # Recursively search subdirectories
                sub_matches = search_recursive(item_path, depth + 1, max_depth)
                matches.extend(sub_matches)
        
        return matches
    
    try:
        matches = search_recursive()
        
        # Sort by relevance (exact matches first, then by name)
        def sort_key(match):
            name = match["name"].lower()
            pattern_lower = pattern.lower() if pattern else ""
            if pattern_lower and pattern_lower in name:
                # Exact pattern match gets higher priority
                if name.startswith(pattern_lower):
                    return (0, name)
                else:
                    return (1, name)
            return (2, name)
        
        matches.sort(key=sort_key)
        
        if not matches:
            return [{
                "message": f"No files found matching pattern '{pattern}' and type '{file_type}'",
                "suggestions": [
                    "Try a broader pattern",
                    "Check the directory structure with list_ryzenai_sw_directory()",
                    "Use search_ryzenai_sw_enhanced() for semantic search"
                ]
            }]
        
        return matches
        
    except Exception as e:
        return [{"error": f"Error searching files: {str(e)}"}]

@mcp.tool(
    name="get_enhanced_embedding_status",
    description="Get status of the enhanced embedding index with smart chunking."
)
def get_enhanced_embedding_status() -> Dict[str, Any]:
    """Get information about the current enhanced embedding index status."""
    store = get_enhanced_store()
    
    # Check database
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM files')
    total_files = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM files WHERE embedding_generated = TRUE')
    embedded_files = cursor.fetchone()[0]
    
    # Get chunking method statistics
    cursor.execute('SELECT chunking_method, COUNT(*) FROM files GROUP BY chunking_method')
    chunking_stats = dict(cursor.fetchall())
    
    conn.close()
    
    last_refresh = store.get_last_refresh_time()
    refresh_hours = float(os.environ.get("RYZENAI_INDEX_REFRESH_HOURS", "24"))
    
    return {
        "embedding_libraries_available": EMBEDDINGS_AVAILABLE and CHROMA_AVAILABLE,
        "hybrid_chunking_available": HYBRID_CHUNKING_AVAILABLE,
        "langchain_tree_sitter_available": LANGCHAIN_TREE_SITTER_AVAILABLE,
        "chunker_type": "LangChain Enhanced" if LANGCHAIN_TREE_SITTER_AVAILABLE else ("Hybrid Tree-sitter" if HYBRID_CHUNKING_AVAILABLE else "Simple Text"),
        "total_files_downloaded": total_files,
        "files_with_embeddings": embedded_files,
        "embedding_coverage": f"{embedded_files}/{total_files}" if total_files > 0 else "0/0",
        "chunking_methods": chunking_stats,
        "database_path": str(store.db_path),
        "chroma_path": str(store.repo_path / "chroma_db") if CHROMA_AVAILABLE else "Not available",
        "auto_refresh_hours": refresh_hours if refresh_hours > 0 else None,
        "last_refresh_timestamp": last_refresh,
        "last_refresh_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_refresh)) if last_refresh else None,
    }

@mcp.tool(
    name="refresh_ryzenai_index",
    description="Clear the embedding index and re-download/re-index the Ryzen AI repo and docs. Use this when the repository or documentation has been updated (e.g. new RAI release) so the MCP server uses the latest content."
)
def refresh_ryzenai_index(max_files="500", github_token=None):
    """
    Refresh the index by clearing existing embeddings and file metadata, then re-downloading
    and re-indexing the AMD RyzenAI repository. Call this when the repo or docs have changed
    (e.g. after a new Ryzen AI release) so semantic search uses up-to-date content.

    Args:
      max_files number of files to download and index (default 100)
      github_token GitHub token for higher rate limits (optional)

    Returns:
      Dictionary with refresh results (cleared, files_downloaded, embeddings_generated)
    """
    max_files = int(max_files)
    store = get_enhanced_store()

    if not EMBEDDINGS_AVAILABLE:
        return {
            "success": False,
            "error": "sentence-transformers not available. Install with: pip install sentence-transformers",
            "cleared": False,
            "files_downloaded": 0,
            "embeddings_generated": 0,
        }

    if not CHROMA_AVAILABLE:
        return {
            "success": False,
            "error": "chromadb not available. Install with: pip install chromadb",
            "cleared": False,
            "files_downloaded": 0,
            "embeddings_generated": 0,
        }

    try:
        store.clear_index()
        files_downloaded = store.download_repository(max_files, github_token)
        embeddings_generated = store.generate_embeddings()
        store.set_last_refresh_time()
        return {
            "success": True,
            "cleared": True,
            "files_downloaded": files_downloaded,
            "embeddings_generated": embeddings_generated,
            "message": f"Index refreshed: cleared old data, downloaded {files_downloaded} files, generated {embeddings_generated} embeddings.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cleared": True,
            "files_downloaded": 0,
            "embeddings_generated": 0,
        }

if __name__ == "__main__":
    import sys, traceback
    try:
        mcp.run()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        raise
