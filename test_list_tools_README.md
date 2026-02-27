# Test List Tools - Simple MCP Client Test

## Purpose

This script (`test_list_tools.py`) connects to the AMD Ryzen AI MCP server and lists all available tools with their descriptions and parameters.

## Usage

### Prerequisites

1. Activate the conda environment with MCP installed:
   ```bash
   conda activate mcp_amd_ryzenai
   ```

2. Navigate to the repository directory:
   ```bash
   cd amd_ryzenai_mcp
   ```

### Run the Test

```bash
python test_list_tools.py
```

## What It Does

1. **Starts the MCP server** as a subprocess
2. **Initializes MCP connection** using JSON-RPC protocol
3. **Requests list of tools** using `tools/list` method
4. **Displays all tools** with:
   - Tool name
   - Description
   - Parameters (with types and whether required/optional)
5. **Cleans up** by stopping the server

## Expected Output

The script will display:

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

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'mcp'"

**Solution:** Make sure you're in the correct conda environment:
```bash
conda activate mcp_amd_ryzenai
```

### Error: "Server failed to start"

**Solution:** Check that:
- All dependencies are installed: `pip install -r requirements.txt`
- Python version is 3.8+: `python --version`
- Server file exists: `ls server.py`

### No tools listed

**Solution:** 
- Check server logs for errors
- Verify MCP protocol communication is working
- Try increasing sleep times in the script

## What This Test Verifies

✅ MCP server starts correctly  
✅ MCP protocol communication works  
✅ Server responds to `initialize` request  
✅ Server responds to `tools/list` request  
✅ All 8 tools are registered correctly  
✅ Tool descriptions and parameters are correct  

This is a useful test to verify your MCP server is working before using it in Cursor!

