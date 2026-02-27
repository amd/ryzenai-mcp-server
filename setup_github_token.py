#!/usr/bin/env python3
# Copyright(C) 2026 Advanced Micro Devices, Inc. All rights reserved.
"""
Simple script to help set up GitHub token for MCP server
"""

import os
import sys

def setup_github_token():
    print("=== GitHub Token Setup for MCP Server ===\n")
    
    # Check if token already exists
    existing_token = os.getenv('GITHUB_TOKEN')
    if existing_token:
        print(f"✅ GITHUB_TOKEN already set: {existing_token[:8]}...")
        print("You're all set! The MCP server will use this token automatically.\n")
        return True
    
    print("To use GitHub search without rate limits, you need a GitHub token.")
    print("\nSteps to get a token:")
    print("1. Go to: https://github.com/settings/tokens")
    print("2. Click 'Generate new token' -> 'Generate new token (classic)'")
    print("3. Give it a name like 'MCP Server'")
    print("4. Select scopes: 'public_repo' (for public repository access)")
    print("5. Click 'Generate token'")
    print("6. Copy the token (it starts with 'ghp_')")
    
    print("\nOptions to set the token:")
    print("Option 1 - Set environment variable:")
    print("  Windows: set GITHUB_TOKEN=your_token_here")
    print("  Linux/Mac: export GITHUB_TOKEN=your_token_here")
    
    print("\nOption 2 - Create .env file:")
    print("  Create a .env file with: GITHUB_TOKEN=your_token_here")
    
    print("\nOption 3 - Pass token directly to MCP tools:")
    print("  The search_ryzenai_sw tool accepts github_token parameter")
    
    print("\nWithout a token, the server will:")
    print("- Try web scraping (works but limited)")
    print("- Fall back to curated results")
    print("- Still provide useful information")
    
    return False

def test_search():
    print("\n=== Testing Search Functionality ===")
    
    try:
        from server import _github_code_search
        
        print("Testing search without token...")
        results = _github_code_search("python", max_results=3)
        print(f"Found {len(results)} results")
        
        if results:
            print("✅ Search is working!")
            for result in results[:2]:
                print(f"  - {result['path']}")
        else:
            print("⚠️  No results found, but fallback system should work")
            
    except Exception as e:
        print(f"❌ Error testing search: {e}")

if __name__ == "__main__":
    setup_github_token()
    test_search()
    
    print("\n=== Next Steps ===")
    print("1. Get a GitHub token if you want full functionality")
    print("2. Run: python server.py")
    print("3. Test with: python test_github_search.py")
    print("4. The MCP server will work even without a token!")

