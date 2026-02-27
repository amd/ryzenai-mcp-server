#!/usr/bin/env python3
# Copyright(C) 2026 Advanced Micro Devices, Inc. All rights reserved.
"""
Enhanced AST-based code chunking using LangChain's Tree-sitter integration
Combines custom AST chunking with LangChain's TreeSitterSegmenter
"""

import tree_sitter
from tree_sitter import Language, Parser
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import os

# LangChain Tree-sitter imports
LANGCHAIN_TREE_SITTER_AVAILABLE = False
PythonSegmenter = None
JavaScriptSegmenter = None
TypeScriptSegmenter = None
CppSegmenter = None
CSegmenter = None

try:
    from langchain_community.document_loaders.parsers.language.tree_sitter_segmenter import TreeSitterSegmenter
    from langchain.schema import Document
    
    # Try importing available segmenters (some may not exist in all versions)
    try:
        from langchain_community.document_loaders.parsers.language.python import PythonSegmenter
    except ImportError:
        pass
    
    try:
        from langchain_community.document_loaders.parsers.language.javascript import JavaScriptSegmenter
    except ImportError:
        pass
    
    try:
        from langchain_community.document_loaders.parsers.language.typescript import TypeScriptSegmenter
    except ImportError:
        pass
    
    # C++ and C segmenters may not be available in all versions
    try:
        from langchain_community.document_loaders.parsers.language.cpp import CppSegmenter
    except ImportError:
        pass
    
    try:
        from langchain_community.document_loaders.parsers.language.c import CSegmenter
    except ImportError:
        pass
    
    # If at least TreeSitterSegmenter and Document are available, we're good
    if TreeSitterSegmenter and Document:
        LANGCHAIN_TREE_SITTER_AVAILABLE = True
except ImportError:
    pass

if not LANGCHAIN_TREE_SITTER_AVAILABLE:
    print("Warning: LangChain Tree-sitter not available. Install with: pip install langchain-community tree-sitter-languages")

@dataclass
class CodeChunk:
    """Represents a semantically meaningful code chunk"""
    content: str
    start_line: int
    end_line: int
    chunk_type: str  # 'function', 'class', 'module', 'import', etc.
    name: str  # function/class name
    parent: Optional[str] = None  # parent class/namespace
    dependencies: List[str] = None  # imports/dependencies used
    metadata: Dict[str, Any] = None  # Additional metadata
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

class LangChainASTChunker:
    """Enhanced AST-based code chunker using LangChain's Tree-sitter integration"""
    
    def __init__(self):
        self.segmenters = {}
        self.custom_parsers = {}
        self._setup_langchain_segmenters()
        self._setup_custom_parsers()
    
    def _setup_langchain_segmenters(self):
        """Setup LangChain Tree-sitter segmenters"""
        if not LANGCHAIN_TREE_SITTER_AVAILABLE:
            return
            
        try:
            # Python segmenter
            self.segmenters['python'] = PythonSegmenter()
            
            # JavaScript segmenter
            self.segmenters['javascript'] = JavaScriptSegmenter()
            
            # TypeScript segmenter
            self.segmenters['typescript'] = TypeScriptSegmenter()
            
            # C++ segmenter
            self.segmenters['cpp'] = CppSegmenter()
            
            # C segmenter
            self.segmenters['c'] = CSegmenter()
            
            print("✅ LangChain Tree-sitter segmenters initialized")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize LangChain segmenters: {e}")
    
    def _setup_custom_parsers(self):
        """Setup custom Tree-sitter parsers as fallback"""
        try:
            # Python parser
            PY_LANGUAGE = Language('build/my-languages.so', 'python')
            self.custom_parsers['python'] = Parser(PY_LANGUAGE)
            
            # C++ parser
            CPP_LANGUAGE = Language('build/my-languages.so', 'cpp')
            self.custom_parsers['cpp'] = Parser(CPP_LANGUAGE)
            
            # C parser
            C_LANGUAGE = Language('build/my-languages.so', 'c')
            self.custom_parsers['c'] = Parser(C_LANGUAGE)
            
            print("✅ Custom Tree-sitter parsers initialized")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize custom parsers: {e}")
    
    def get_language_from_extension(self, file_path: str) -> str:
        """Determine language from file extension"""
        ext = file_path.split('.')[-1].lower()
        
        language_map = {
            'py': 'python',
            'pyi': 'python',
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'cpp': 'cpp',
            'cc': 'cpp',
            'cxx': 'cpp',
            'c++': 'cpp',
            'hpp': 'cpp',
            'hxx': 'cpp',
            'c': 'c',
            'h': 'c'
        }
        
        return language_map.get(ext, 'python')
    
    def chunk_code_langchain(self, code: str, file_path: str) -> List[CodeChunk]:
        """Chunk code using LangChain's Tree-sitter segmenters"""
        if not LANGCHAIN_TREE_SITTER_AVAILABLE:
            return self.chunk_code_custom(code, file_path)
        
        language = self.get_language_from_extension(file_path)
        
        if language not in self.segmenters:
            print(f"⚠️  No LangChain segmenter for {language}, falling back to custom parser")
            return self.chunk_code_custom(code, file_path)
        
        try:
            segmenter = self.segmenters[language]
            
            # Create a Document object
            doc = Document(page_content=code, metadata={"source": file_path})
            
            # Segment the document
            segments = segmenter.segment_document(doc)
            
            # Convert to CodeChunk objects
            chunks = []
            for i, segment in enumerate(segments):
                # Extract metadata from segment
                metadata = segment.metadata or {}
                
                # Determine chunk type from metadata
                chunk_type = metadata.get('type', 'unknown')
                name = metadata.get('name', f'segment_{i}')
                
                # Calculate line numbers (approximate)
                lines = code[:segment.page_content.find(segment.page_content)].count('\n')
                start_line = lines + 1
                end_line = start_line + segment.page_content.count('\n')
                
                chunk = CodeChunk(
                    content=segment.page_content,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type=chunk_type,
                    name=name,
                    parent=metadata.get('parent'),
                    dependencies=metadata.get('dependencies', []),
                    metadata=metadata
                )
                chunks.append(chunk)
            
            print(f"✅ LangChain chunked {file_path}: {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            print(f"⚠️  LangChain chunking failed for {file_path}: {e}")
            return self.chunk_code_custom(code, file_path)
    
    def chunk_code_custom(self, code: str, file_path: str) -> List[CodeChunk]:
        """Fallback custom chunking using direct Tree-sitter parsing"""
        language = self.get_language_from_extension(file_path)
        
        if language not in self.custom_parsers:
            print(f"⚠️  No parser for {language}, using simple text chunking")
            return self._simple_text_chunking(code, file_path)
        
        try:
            parser = self.custom_parsers[language]
            tree = parser.parse(bytes(code, 'utf8'))
            
            chunks = []
            if language == 'python':
                chunks = self._chunk_python_ast(tree, code, file_path)
            elif language in ['cpp', 'c']:
                chunks = self._chunk_cpp_ast(tree, code, file_path)
            else:
                chunks = self._simple_text_chunking(code, file_path)
            
            print(f"✅ Custom chunked {file_path}: {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            print(f"⚠️  Custom chunking failed for {file_path}: {e}")
            return self._simple_text_chunking(code, file_path)
    
    def _chunk_python_ast(self, tree, code: str, file_path: str) -> List[CodeChunk]:
        """Chunk Python code using AST analysis"""
        chunks = []
        lines = code.split('\n')
        
        def traverse_node(node, parent_name=None):
            if node.type == 'function_definition':
                name = self._extract_name(node, code)
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                content = '\n'.join(lines[start_line-1:end_line])
                
                chunk = CodeChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type='function',
                    name=name,
                    parent=parent_name,
                    dependencies=self._extract_imports(code),
                    metadata={'node_type': node.type}
                )
                chunks.append(chunk)
                
                # Recursively process nested functions
                for child in node.children:
                    traverse_node(child, name)
                    
            elif node.type == 'class_definition':
                name = self._extract_name(node, code)
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                content = '\n'.join(lines[start_line-1:end_line])
                
                chunk = CodeChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type='class',
                    name=name,
                    parent=parent_name,
                    dependencies=self._extract_imports(code),
                    metadata={'node_type': node.type}
                )
                chunks.append(chunk)
                
                # Process methods in the class
                for child in node.children:
                    traverse_node(child, name)
        
        # Traverse the AST
        for child in tree.root_node.children:
            traverse_node(child)
        
        return chunks
    
    def _chunk_cpp_ast(self, tree, code: str, file_path: str) -> List[CodeChunk]:
        """Chunk C++ code using AST analysis"""
        chunks = []
        lines = code.split('\n')
        
        def traverse_node(node, parent_name=None):
            if node.type in ['function_definition', 'method_definition']:
                name = self._extract_name(node, code)
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                content = '\n'.join(lines[start_line-1:end_line])
                
                chunk = CodeChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type='function',
                    name=name,
                    parent=parent_name,
                    dependencies=self._extract_includes(code),
                    metadata={'node_type': node.type}
                )
                chunks.append(chunk)
                
            elif node.type in ['class_specifier', 'struct_specifier']:
                name = self._extract_name(node, code)
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                content = '\n'.join(lines[start_line-1:end_line])
                
                chunk = CodeChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type='class',
                    name=name,
                    parent=parent_name,
                    dependencies=self._extract_includes(code),
                    metadata={'node_type': node.type}
                )
                chunks.append(chunk)
                
                # Process methods in the class
                for child in node.children:
                    traverse_node(child, name)
        
        # Traverse the AST
        for child in tree.root_node.children:
            traverse_node(child)
        
        return chunks
    
    def _extract_name(self, node, code: str) -> str:
        """Extract name from AST node"""
        for child in node.children:
            if child.type in ['identifier', 'name']:
                return code[child.start_byte:child.end_byte]
        return 'unknown'
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements from Python code"""
        imports = []
        lines = code.split('\n')
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                imports.append(line.strip())
        return imports
    
    def _extract_includes(self, code: str) -> List[str]:
        """Extract include statements from C++ code"""
        includes = []
        lines = code.split('\n')
        for line in lines:
            if line.strip().startswith('#include'):
                includes.append(line.strip())
        return includes
    
    def _simple_text_chunking(self, code: str, file_path: str) -> List[CodeChunk]:
        """Fallback simple text chunking"""
        lines = code.split('\n')
        chunk_size = 50  # lines per chunk
        
        chunks = []
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            content = '\n'.join(chunk_lines)
            
            chunk = CodeChunk(
                content=content,
                start_line=i + 1,
                end_line=min(i + chunk_size, len(lines)),
                chunk_type='text_block',
                name=f'block_{i//chunk_size + 1}',
                parent=None,
                dependencies=[],
                metadata={'chunking_method': 'simple_text'}
            )
            chunks.append(chunk)
        
        return chunks
    
    def chunk_code(self, code: str, file_path: str) -> List[CodeChunk]:
        """Main chunking method - tries LangChain first, falls back to custom"""
        if LANGCHAIN_TREE_SITTER_AVAILABLE:
            return self.chunk_code_langchain(code, file_path)
        else:
            return self.chunk_code_custom(code, file_path)
    
    def chunk_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Chunk a file and return LangChain-compatible documents"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []
        
        chunks = self.chunk_code(code, file_path)
        
        # Convert to LangChain Document format
        documents = []
        for chunk in chunks:
            doc = Document(
                page_content=chunk.content,
                metadata={
                    'source': file_path,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                    'chunk_type': chunk.chunk_type,
                    'name': chunk.name,
                    'parent': chunk.parent,
                    'dependencies': chunk.dependencies,
                    **chunk.metadata
                }
            )
            documents.append(doc)
        
        return documents

def main():
    """Test the enhanced AST chunker"""
    print("🧪 Testing Enhanced LangChain AST Chunker")
    print("=" * 50)
    
    chunker = LangChainASTChunker()
    
    # Test Python code
    python_code = '''
def hello_world():
    """A simple hello world function"""
    print("Hello, World!")
    return "success"

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
'''
    
    print("\n🐍 Testing Python chunking...")
    chunks = chunker.chunk_code(python_code, 'test.py')
    for chunk in chunks:
        print(f"  {chunk.chunk_type}: {chunk.name} (lines {chunk.start_line}-{chunk.end_line})")
    
    # Test C++ code
    cpp_code = '''
#include <iostream>

class Calculator {
public:
    int add(int a, int b) {
        return a + b;
    }
    
    int multiply(int a, int b) {
        return a * b;
    }
};

int main() {
    Calculator calc;
    std::cout << calc.add(5, 3) << std::endl;
    return 0;
}
'''
    
    print("\n🔧 Testing C++ chunking...")
    chunks = chunker.chunk_code(cpp_code, 'test.cpp')
    for chunk in chunks:
        print(f"  {chunk.chunk_type}: {chunk.name} (lines {chunk.start_line}-{chunk.end_line})")
    
    print(f"\n✅ Enhanced AST chunker test completed!")
    print(f"   LangChain Tree-sitter available: {LANGCHAIN_TREE_SITTER_AVAILABLE}")

if __name__ == "__main__":
    main()
