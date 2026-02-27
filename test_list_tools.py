#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright(C) 2026 Advanced Micro Devices, Inc. All rights reserved.
"""
Simple MCP Client Test - List Available Tools
This script connects to the MCP server and lists all available tools.
"""

import json
import subprocess
import sys
import io
import time
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        if sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def list_mcp_tools():
    """Connect to MCP server and list all available tools"""
    
    print("=" * 70)
    print("AMD Ryzen AI MCP Server - Tool Lister")
    print("=" * 70)
    print()
    
    # Get the server.py path (assume we're in the same directory)
    script_dir = Path(__file__).parent.resolve()
    server_path = script_dir / "server.py"
    
    # Use the current Python interpreter
    python_exe = sys.executable
    
    print(f"Server script: {server_path}")
    print(f"Python: {python_exe}")
    print()
    print("NOTE: Make sure you're in the correct conda environment with MCP installed!")
    print("      Run: conda activate mcp_amd_ryzenai")
    print()
    
    # Start the server process
    print("Starting MCP server...")
    try:
        server_process = subprocess.Popen(
            [python_exe, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Give server time to initialize
        time.sleep(2)
        
        # Check if server is still running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print("[ERROR] Server failed to start!")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
        
        print("[OK] Server started successfully")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error starting server: {e}")
        return False
    
    try:
        # Step 1: Initialize MCP connection
        print("Step 1: Initializing MCP connection...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "tool-lister-client",
                    "version": "1.0.0"
                }
            }
        }
        
        server_process.stdin.write(json.dumps(init_request) + "\n")
        server_process.stdin.flush()
        
        # Wait for response - read lines until we get a JSON response
        time.sleep(1)
        init_response = None
        for _ in range(10):  # Try up to 10 lines
            line = server_process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            # Skip warning lines (they don't start with {)
            if line.startswith('{'):
                try:
                    init_response = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        if init_response and "result" in init_response:
            print("[OK] MCP connection initialized")
            print(f"   Server: {init_response['result'].get('serverInfo', {}).get('name', 'Unknown')}")
            print(f"   Version: {init_response['result'].get('serverInfo', {}).get('version', 'Unknown')}")
        else:
            print("[WARNING] Could not get initialization response")
            if init_response:
                print(f"Response: {init_response}")
        
        print()
        
        # Step 2: Send initialized notification
        print("Step 2: Sending 'initialized' notification...")
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        server_process.stdin.write(json.dumps(initialized_notification) + "\n")
        server_process.stdin.flush()
        time.sleep(0.5)
        print("[OK] Notification sent")
        print()
        
        # Step 3: List available tools
        print("Step 3: Requesting list of available tools...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        server_process.stdin.write(json.dumps(tools_request) + "\n")
        server_process.stdin.flush()
        
        # Wait for response - read lines until we get a JSON response
        time.sleep(1)
        tools_response = None
        tools_response_line = None
        
        for _ in range(10):  # Try up to 10 lines
            line = server_process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            # Skip warning lines (they don't start with {)
            if line.startswith('{'):
                tools_response_line = line
                try:
                    tools_response = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        if tools_response:
            try:
                
                if "result" in tools_response and "tools" in tools_response["result"]:
                    tools = tools_response["result"]["tools"]
                    
                    print("=" * 70)
                    print(f"[SUCCESS] Found {len(tools)} Available MCP Tools")
                    print("=" * 70)
                    print()
                    
                    for i, tool in enumerate(tools, 1):
                        name = tool.get("name", "Unknown")
                        description = tool.get("description", "No description")
                        
                        # Get input schema if available
                        input_schema = tool.get("inputSchema", {})
                        properties = input_schema.get("properties", {})
                        
                        print(f"{i}. {name}")
                        print(f"   Description: {description}")
                        
                        if properties:
                            print("   Parameters:")
                            for param_name, param_info in properties.items():
                                param_type = param_info.get("type", "unknown")
                                param_desc = param_info.get("description", "")
                                required = param_name in input_schema.get("required", [])
                                req_marker = " (required)" if required else " (optional)"
                                print(f"     - {param_name}: {param_type}{req_marker}")
                                if param_desc:
                                    print(f"       {param_desc}")
                        
                        print()
                    
                    print("=" * 70)
                    print("[SUCCESS] Tool listing complete!")
                    print("=" * 70)
                    
                else:
                    print("[ERROR] No tools found in response")
                    print(f"Response: {json.dumps(tools_response, indent=2)}")
                    
            except Exception as e:
                print(f"[ERROR] Error processing tools response: {e}")
                print(f"Response: {tools_response}")
        else:
            print("[ERROR] No valid JSON response received for tools/list request")
            if tools_response_line:
                print(f"Last line read: {tools_response_line[:200]}")
            # Try to read any error output
            try:
                server_process.wait(timeout=1)
                stdout, stderr = server_process.communicate()
                if stderr:
                    print(f"STDERR: {stderr}")
            except:
                pass
        
    except Exception as e:
        print(f"[ERROR] Error during tool listing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print()
        print("Cleaning up...")
        try:
            server_process.terminate()
            server_process.wait(timeout=3)
            print("[OK] Server stopped")
        except:
            try:
                server_process.kill()
                print("[WARNING] Server force-killed")
            except:
                pass
    
    return True

if __name__ == "__main__":
    try:
        success = list_mcp_tools()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Interrupted by user")
        sys.exit(1)

