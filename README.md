# AMD Ryzen AI MCP Server

AMD Ryzen AI Model Context Protocol (MCP) Server for Cursor IDE.

This MCP server provides semantic search and access to AMD Ryzen AI documentation and code examples from the [amd/RyzenAI-SW](https://github.com/amd/RyzenAI-SW) repository and [AMD Ryzen AI documentation](https://ryzenai.docs.amd.com).

## Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/amd/ryzenai-mcp-server
   cd ryzenai-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the server:**
   - The server will work out of the box
   - Optionally set `GITHUB_TOKEN` environment variable for higher GitHub API rate limits
   - Get a token from [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)

### Configuration

The server supports the following environment variables:

- `GITHUB_TOKEN` (optional): GitHub personal access token for higher API rate limits. Requires `public_repo` scope.
- `RYZENAI_INDEX_REFRESH_HOURS` (optional): Hours between automatic index refreshes. Default **24**. Set to **0** to disable auto-refresh.
- `RYZENAI_INDEX_MAX_FILES` (optional): Max files to download per refresh (used by auto-refresh and by the refresh tool). Default **100**.

## Features

- ✅ **Semantic Search**: AI-powered semantic search of AMD Ryzen AI repository using embeddings
- ✅ **Enhanced Code Chunking**: Tree-sitter AST-based chunking for better code understanding
- ✅ **Documentation Access**: Read AMD Ryzen AI documentation pages directly
- ✅ **Repository Browsing**: List directories, find files, and read code from the repository
- ✅ **Smart Indexing**: Automatic download and indexing of repository files with embeddings

## Available Tools

The MCP server provides 9 tools:

1. **read_ryzenai** - Read AMD Ryzen AI documentation pages
2. **search_ryzenai_sw_keyword** - Keyword search in the Ryzen AI repository
3. **search_ryzenai_sw_enhanced** - Enhanced semantic search with AI embeddings
4. **read_ryzenai_sw** - Read specific files from the repository
5. **list_ryzenai_sw_directory** - List contents of a directory
6. **find_ryzenai_sw_files** - Find files by name pattern or type
7. **download_and_index_ryzenai_enhanced** - Download and index repository with AI embeddings
8. **get_enhanced_embedding_status** - Check embedding index status
9. **refresh_ryzenai_index** - Clear the index and re-download/re-index (use after repo or docs updates)

## Refreshing the index

The index is **refreshed automatically every 24 hours** (configurable via `RYZENAI_INDEX_REFRESH_HOURS`). A background thread clears the embedding store and re-downloads/re-indexes the repository so you get the latest Ryzen AI repo and docs without doing anything.

- **Default**: refresh every **24 hours** (reasonable for tracking upstream releases).
- **Disable**: set `RYZENAI_INDEX_REFRESH_HOURS=0`.
- **Manual refresh**: you can still ask the AI to run **refresh_ryzenai_index** anytime (e.g. *"Refresh the Ryzen AI MCP index"*); that also resets the 24h timer.
- **Status**: use **get_enhanced_embedding_status** to see `last_refresh_iso` and `auto_refresh_hours`.

## Usage Examples

Once installed in Cursor, you can ask:

- "Find inference examples for Llama models"
- "Read the getting started guide from Ryzen AI docs"
- "Write the python code to compile and run resnet50 model on AMD RyzenAI NPU"
- "Write the python code to compile and run the distilbert-base-uncased-finetuned-sst-2-english model (the fine-tuned checkpoint of DistilBERT-base-uncased, trained on the SST-2 dataset)"

## Requirements

See `requirements.txt` for full dependency list. Key dependencies include:

- `mcp>=1.14.0` - Model Context Protocol
- `sentence-transformers>=2.2.0` - For AI embeddings
- `chromadb>=0.4.0` - Vector database
- `langchain-community>=0.0.20` - For text chunking
- `tree-sitter-languages>=1.10.0` - For AST-based code chunking

## Documentation

For detailed setup instructions, see `README_SETUP.md`.

## Repository

- **GitHub**: https://github.com/amd/ryzenai-mcp-server
- **AMD Ryzen AI Docs**: https://ryzenai.docs.amd.com
- **RyzenAI-SW Repository**: https://github.com/amd/RyzenAI-SW

## License

MIT License

