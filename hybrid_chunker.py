#!/usr/bin/env python3
# Copyright(C) 2026 Advanced Micro Devices, Inc. All rights reserved.
"""
Hybrid chunking strategy: Tree-sitter for code, LangChain for documentation
Best of both worlds - AST-aware code chunking + smart text chunking
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

# Try to import LangChain AST chunker (preferred)
try:
    from ast_chunker_langchain import LangChainASTChunker, CodeChunk
    LANGCHAIN_AST_AVAILABLE = True
except ImportError:
    LANGCHAIN_AST_AVAILABLE = False
    CodeChunk = None

# LangChain imports
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

class HybridChunker:
    """Hybrid chunker: Tree-sitter for code, LangChain for text"""
    
    def __init__(self):
        # Try to use LangChain AST chunker if available
        if LANGCHAIN_AST_AVAILABLE:
            try:
                self.ast_chunker = LangChainASTChunker()
                self.use_ast_chunking = True
            except Exception as e:
                print(f"Warning: Could not initialize LangChain AST chunker: {e}")
                self.ast_chunker = None
                self.use_ast_chunking = False
        else:
            self.ast_chunker = None
            self.use_ast_chunking = False
        
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", " ", ""]
            )
        else:
            self.text_splitter = None
    
    def get_file_type(self, file_path: str) -> str:
        """Determine file type for appropriate chunking strategy"""
        ext = file_path.split('.')[-1].lower()
        
        # Code files - use AST chunking (Python, C++, C)
        code_extensions = {'.py', '.pyi', '.cpp', '.cc', '.cxx', '.c++', '.hpp', '.hxx', '.c', '.h'}
        if ext in code_extensions:
            return 'code'
        
        # Documentation files - use text chunking
        doc_extensions = {'.md', '.txt', '.rst', '.yml', '.yaml', '.json', '.cfg', '.ini'}
        if ext in doc_extensions:
            return 'documentation'
        
        # Default to text chunking
        return 'text'
    
    def chunk_file(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk file using appropriate strategy based on file type"""
        file_type = self.get_file_type(file_path)
        
        if file_type == 'code':
            return self._chunk_code_file(content, file_path)
        else:
            return self._chunk_text_file(content, file_path)
    
    def _chunk_code_file(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk code file using Tree-sitter AST"""
        print(f"🔧 AST chunking: {file_path}")
        
        # Try AST-based chunking if available
        if self.use_ast_chunking and self.ast_chunker:
            try:
                # Use LangChainASTChunker.chunk_code which takes content and file_path
                chunks = self.ast_chunker.chunk_code(content, file_path)
                
                # Convert CodeChunk objects to document format
                documents = []
                for chunk in chunks:
                    doc = {
                        "content": chunk.content,
                        "metadata": {
                            "path": file_path,
                            "file_type": file_path.split('.')[-1],
                            "chunk_type": chunk.chunk_type,
                            "chunk_name": chunk.name,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "parent": chunk.parent,
                            "dependencies": chunk.dependencies if chunk.dependencies else [],
                            "chunking_method": "ast_tree_sitter",
                            "source": f"https://github.com/amd/RyzenAI-SW/blob/HEAD/{file_path}"
                        }
                    }
                    documents.append(doc)
                
                return documents
            except Exception as e:
                print(f"⚠️  AST chunking failed: {e}, falling back to simple chunking")
        
        # Fallback to simple text chunking for code
        return self._chunk_text_file(content, file_path)
    
    def _chunk_text_file(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk text file using LangChain text splitter"""
        print(f"📄 Text chunking: {file_path}")
        
        if self.text_splitter:
            # Use LangChain text splitter
            chunks = self.text_splitter.split_text(content)
        else:
            # Fallback to simple chunking
            chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
        
        # Convert to document format
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                "content": chunk,
                "metadata": {
                    "path": file_path,
                    "file_type": file_path.split('.')[-1],
                    "chunk_type": "text",
                    "chunk_name": f"chunk_{i+1}",
                    "chunk_index": i,
                    "chunking_method": "langchain_text" if self.text_splitter else "simple_text",
                    "source": f"https://github.com/amd/RyzenAI-SW/blob/HEAD/{file_path}"
                }
            }
            documents.append(doc)
        
        return documents
    
    def chunk_directory(self, directory_path: str, max_files: int = 100) -> List[Dict[str, Any]]:
        """Chunk all files in directory using hybrid strategy"""
        all_documents = []
        files_processed = 0
        
        directory = Path(directory_path)
        
        for file_path in directory.rglob("*"):
            if files_processed >= max_files:
                break
                
            if file_path.is_file():
                try:
                    # Read file content
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Skip empty or very small files
                    if len(content.strip()) < 50:
                        continue
                    
                    # Chunk file
                    documents = self.chunk_file(content, str(file_path))
                    all_documents.extend(documents)
                    files_processed += 1
                    
                    print(f"✅ Processed {file_path.name}: {len(documents)} chunks")
                    
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {e}")
                    continue
        
        print(f"\n📊 Chunking Summary:")
        print(f"   Files processed: {files_processed}")
        print(f"   Total chunks: {len(all_documents)}")
        
        # Analyze chunking methods
        ast_chunks = sum(1 for doc in all_documents if doc['metadata']['chunking_method'] == 'ast_tree_sitter')
        text_chunks = sum(1 for doc in all_documents if doc['metadata']['chunking_method'].startswith('langchain_text'))
        simple_chunks = sum(1 for doc in all_documents if doc['metadata']['chunking_method'] == 'simple_text')
        
        print(f"   AST chunks: {ast_chunks}")
        print(f"   LangChain text chunks: {text_chunks}")
        print(f"   Simple text chunks: {simple_chunks}")
        
        return all_documents

# Example usage and comparison
if __name__ == "__main__":
    chunker = HybridChunker()
    
    # Example Python code
    python_code = '''
import numpy as np
import torch
from typing import List, Dict

class ModelTrainer:
    """A class for training machine learning models"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.model = None
    
    def train(self, data: np.ndarray) -> None:
        """Train the model on provided data"""
        # Training logic here
        pass
    
    def evaluate(self, test_data: np.ndarray) -> float:
        """Evaluate model performance"""
        # Evaluation logic here
        return 0.95

def load_data(path: str) -> np.ndarray:
    """Load data from file"""
    return np.load(path)
'''
    
    # Example Markdown documentation
    markdown_content = '''
# AMD Ryzen AI Documentation

## Getting Started

This guide will help you get started with AMD Ryzen AI development.

### Prerequisites

- Python 3.8+
- AMD Ryzen AI SDK
- ONNX Runtime

### Installation

1. Install the AMD Ryzen AI SDK
2. Install Python dependencies
3. Configure your environment

## Examples

### Basic Usage

```python
import amd_ryzenai
# Your code here
```

### Advanced Configuration

For advanced users, you can customize the configuration.
'''
    
    print("🧪 Testing Hybrid Chunking Strategy")
    print("=" * 50)
    
    # Test Python code chunking
    print("\n🐍 Python Code Chunking (AST-based):")
    python_docs = chunker.chunk_file(python_code, "example.py")
    for i, doc in enumerate(python_docs, 1):
        metadata = doc['metadata']
        print(f"  Chunk {i}: {metadata['chunk_type']} - {metadata['chunk_name']}")
        print(f"    Lines: {metadata['start_line']}-{metadata['end_line']}")
        print(f"    Method: {metadata['chunking_method']}")
        print(f"    Preview: {doc['content'][:80]}...")
        print()
    
    # Test Markdown chunking
    print("\n📝 Markdown Chunking (LangChain-based):")
    markdown_docs = chunker.chunk_file(markdown_content, "README.md")
    for i, doc in enumerate(markdown_docs, 1):
        metadata = doc['metadata']
        print(f"  Chunk {i}: {metadata['chunk_type']} - {metadata['chunk_name']}")
        print(f"    Method: {metadata['chunking_method']}")
        print(f"    Preview: {doc['content'][:80]}...")
        print()
