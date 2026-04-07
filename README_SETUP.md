# AMD Ryzen AI MCP Server - Setup Guide

This guide will help you set up the AMD Ryzen AI MCP (Model Context Protocol) server on a new laptop.

## 🎯 What is this?

The AMD Ryzen AI MCP Server is a tool that provides access to AMD Ryzen AI documentation and code examples directly in Cursor IDE. It uses semantic search, AI embeddings, and smart code chunking to help you find relevant information quickly.

## 📋 Prerequisites

- **Windows** 10 or later, or **Linux** (Ubuntu 20.04+), or **macOS** 11.0+
- **Python** 3.8 or higher
- **Conda** or **Miniconda** installed
- **Cursor IDE** installed
- **Git** installed (optional, for version control)

## 🚀 Installation Steps

### Step 1: Create a Conda Environment

Open your terminal (PowerShell on Windows, Terminal on Linux/Mac) and run:

```bash
# Create a new conda environment with Python 3.10
conda create -n mcp_amd_ryzenai python=3.10 -y

# Activate the environment
conda activate mcp_amd_ryzenai
```

### Step 2: Clone or Copy the MCP Files

If using Git:
```bash
# Clone the repository
git clone <repository_url>
cd <repository_directory>
```

If copying files manually:
1. Copy all files from the MCP directory to your new location
2. Navigate to that directory in terminal

### Step 3: Install Dependencies

While the conda environment is activated, install the required packages:

```bash
# Install from requirements.txt
pip install -r requirements.txt
```

**Note:** This installation may take 10-20 minutes as it downloads:
- PyTorch (for machine learning)
- sentence-transformers (for AI embeddings)
- chromadb (for vector database)
- langchain-community (for text chunking)
- tree-sitter (for code analysis)

### Step 4: (Optional) Install Tree-sitter Languages

For enhanced code chunking:

```bash
# Build Tree-sitter language support
# This is optional but recommended for better code understanding
pip install tree-sitter-languages --upgrade
```

### Step 5: Test the Installation

Test that everything is working using the provided test script:

```bash
# Make sure you're in the correct conda environment
conda activate mcp_amd_ryzenai

# Navigate to the MCP directory
cd amd_ryzenai_mcp

# Run the tool listing test
python test_list_tools.py
```

**Expected Output:**
```
======================================================================
[SUCCESS] Found 8 Available MCP Tools
======================================================================

1. read_ryzenai
   Description: Read and extract text from a Ryzen AI docs page...
   Parameters:
     - path_or_url: string (required)
     - max_chars: string (optional)

2. download_and_index_ryzenai_enhanced
   ...

... (all 8 tools listed)
```

If you see all 8 tools listed with their descriptions, the installation is successful!


## 🔧 Cursor IDE Integration

### Step 1: Locate Cursor's Configuration

**Windows:**
- Configuration file location: `%APPDATA%\Cursor\User\settings.json`

**Linux:**
- Configuration file location: `~/.config/Cursor/User/settings.json`

**macOS:**
- Configuration file location: `~/Library/Application Support/Cursor/User/settings.json`

### Step 2: Configure MCP Server

Open the Cursor configuration file and add the MCP server settings:

```json
{
  "mcpServers": {
    "amd-ryzenai": {
      "command": "<path_to_python_in_conda_env>",
      "args": ["<absolute_path_to_server.py>"],
      "cwd": "<absolute_path_to_MCP_directory>",
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

**Important:** Replace the following placeholders with your actual paths:

**On Windows:**
```json
{
  "mcpServers": {
    "amd-ryzenai": {
      "command": "C:\\Users\\YourName\\miniforge3\\envs\\mcp_amd_ryzenai\\python.exe",
      "args": ["C:\\path\\to\\MCP-Cursor\\MCP\\server.py"],
      "cwd": "C:\\path\\to\\MCP-Cursor\\MCP",
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

**On Linux/Mac:**
```json
{
  "mcpServers": {
    "amd-ryzenai": {
      "command": "/home/yourname/anaconda3/envs/mcp_amd_ryzenai/bin/python",
      "args": ["/path/to/MCP-Cursor/Mhereum/eth/CP/server.py"],
      "cwd": "/path/to/MCP-Cursor/MCP",
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Step 3: (Optional) Set Up GitHub Token

For better search results without rate limits, you can add a GitHub token:

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name like "MCP Server"
4. Select scope: `public_repo`
5. Generate and copy the token

Then add it to the Cursor configuration:

```json
{
  "mcpServers": {
    "amd-ryzenai": {
      "command": "<path_to_python>",
      "args": ["<path_to_server.py>"],
      "cwd": "<path_to_MCP_directory>",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

### Step 4: Restart Cursor IDE

1. Close Cursor completely
2. Reopen Cursor
3. The MCP server should now be connected

## ✅ Verification

To verify the MCP server is working in Cursor:

1. Open Cursor IDE
2. Start a new chat or conversation
3. Try asking: "Search for ResNet examples in Ryzen AI"
4. The AI should be able to use the MCP tools to search the Ryzen AI documentation

## 🔍 Available MCP Tools

The MCP server provides the following tools:

1. **read_ryzenai** - Read AMD Ryzen AI documentation pages
2. **search_ryzenai_sw_keyword** - Keyword search in the Ryzen AI repository
3. **search_ryzenai_sw_enhanced** - Enhanced semantic search with AI embeddings
4. **read_ryzenai_sw** - Read specific files from the repository
5. **list_ryzenai_sw_directory** - List contents of a directory
6. **find_ryzenai_sw_files** - Find files by name pattern or type
7. **download_and_index_ryzenai_enhanced** - Download and index repository with AI embeddings
8. **get_enhanced_embedding_status** - Check embedding index status

## 🐛 Troubleshooting

### Issue: MCP server not starting

**Solution:**
- Check that Python path in Cursor config is correct
- Ensure conda environment is activated when starting Cursor
- Check Python version: `python --version` (should be 3.8+)

### Issue: Import errors

**Solution:**
```bash
# Reinstall dependencies
conda activate mcp_amd_ryzenai
pip install --upgrade -r requirements.txt
```

### Issue: sentence-transformers not found

**Solution:**
```bash
conda activate mcp_amd_ryzenai
pip install sentence-transformers --upgrade
```

### Issue: chromadb errors

**Solution:**
```bash
conda activate mcp_amd_ryzenai
pip install chromadb --upgrade
```

### Issue: GitHub rate limit errors

**Solution:**
- Add GitHub token to Cursor configuration (see Step 3 above)
- Or wait for the rate limit to reset (typically 1 hour)

### Issue: Tree-sitter chunking not working

**Solution:**
```bash
conda activate mcp_amd_ryzenai
pip install tree-sitter-languages --upgrade
```

## 📁 Important Files

- **server.py** - Main MCP server (enhanced version with embeddings)
- **requirements.txt** - All Python dependencies
- **hybrid_chunker.py** - Hybrid chunking strategy
- **ast_chunker_langchain.py** - Tree-sitter based code chunking
- **setup_github_token.py** - Helper script for GitHub token setup

## 🔄 Updating the MCP Server

To update to the latest version:

```bash
# Activate environment
conda activate mcp_amd_ryzenai

# Navigate to MCP directory
cd path/to/MCP-Cursor/MCP

# Update dependencies
pip install --upgrade -r requirements.txt

# Restart Cursor IDE
```

## 💡 Tips

1. **First-time embedding generation**: The first time you use `search_ryzenai_sw_enhanced`, it may take a few minutes to download and index the repository. Subsequent searches will be much faster.

2. **Offline mode**: The server can work offline after the initial download, but you won't get the latest updates from GitHub.

3. **Performance**: The enhanced semantic search works best with embeddings. If embeddings aren't available, the server falls back to keyword search.

4. **Storage**: The embedded data is stored locally in the `ryzenai_embeddings` directory. This can grow to 500MB+ for a full index.

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review Cursor's MCP server logs
3. Test the server manually using `python server.py`
4. Check Python and package versions

## 🎉 Next Steps

Once set up, try these:

1. Ask Cursor: "Show me examples of using ResNet with Ryzen AI"
2. Search for specific models: "Find Llama inference examples"
3. Browse documentation: "Read the getting started guide"

Happy coding! 🚀


