"""
MCP Client for Digital FTE

Helper script to call MCP server tools via HTTP or stdio.

Usage:
    # List available tools
    uv run python scripts/mcp-client.py list --url http://localhost:8801
    
    # Call a tool
    uv run python scripts/mcp-client.py call --url http://localhost:8801 -t send_email -p '{"to": "test@example.com", "subject": "Test", "body": "Hello"}'
    
    # Call via stdio (for local MCP servers)
    uv run python scripts/mcp-client.py call-stdio -s email -t send_email -p '{"to": "test@example.com"}'
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    print("httpx not installed. Install with: uv add httpx")


def list_tools(server_url: str) -> None:
    """List available tools from MCP server."""
    if not HTTPX_AVAILABLE:
        print("httpx not available")
        return
    
    try:
        response = httpx.get(f"{server_url}/tools")
        response.raise_for_status()
        tools = response.json()
        
        print(f"\nAvailable tools from {server_url}:\n")
        print("-" * 60)
        
        for tool in tools:
            print(f"\n{tool.get('name', 'unknown')}")
            print(f"  Description: {tool.get('description', 'No description')}")
            if 'inputSchema' in tool:
                schema = tool['inputSchema']
                if 'properties' in schema:
                    print("  Parameters:")
                    for param, details in schema['properties'].items():
                        required = param in schema.get('required', [])
                        print(f"    - {param} {'(required)' if required else '(optional)'}: {details.get('description', '')}")
        
        print("\n" + "-" * 60)
        
    except httpx.ConnectError:
        print(f"Could not connect to {server_url}")
        print("Make sure the MCP server is running.")
    except Exception as e:
        print(f"Error: {e}")


def call_tool(server_url: str, tool_name: str, params: dict) -> None:
    """Call a tool on MCP server."""
    if not HTTPX_AVAILABLE:
        print("httpx not available")
        return
    
    try:
        response = httpx.post(
            f"{server_url}/tools/{tool_name}/invoke",
            json=params,
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"\nTool: {tool_name}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
    except httpx.ConnectError:
        print(f"Could not connect to {server_url}")
        print("Make sure the MCP server is running.")
    except httpx.TimeoutException:
        print("Request timed out")
    except Exception as e:
        print(f"Error: {e}")


def call_tool_stdio(server_name: str, tool_name: str, params: dict) -> None:
    """Call a tool on MCP server via stdio transport."""
    import subprocess
    
    mcp_servers = {
        'email': 'mcp-servers/email/server.py',
        'linkedin': 'mcp-servers/linkedin/server.py'
    }
    
    if server_name not in mcp_servers:
        print(f"Unknown server: {server_name}")
        print(f"Available: {list(mcp_servers.keys())}")
        return
    
    server_path = Path(__file__).parent.parent / mcp_servers[server_name]
    
    if not server_path.exists():
        print(f"Server not found: {server_path}")
        return
    
    # For stdio, we'd need to implement MCP protocol
    # This is a simplified version
    print(f"Calling {tool_name} on {server_name} via stdio...")
    print("Note: Full stdio implementation requires MCP protocol handling.")
    print("Use HTTP transport for now:")
    print(f"  uv run python {server_path} --transport http --port 8801")
    print(f"  uv run python scripts/mcp-client.py call --url http://localhost:8801 -t {tool_name} ...")


def main():
    parser = argparse.ArgumentParser(description='MCP Client for Digital FTE')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available tools')
    list_parser.add_argument('--url', required=True, help='MCP server URL')
    
    # Call command
    call_parser = subparsers.add_parser('call', help='Call a tool')
    call_parser.add_argument('--url', required=True, help='MCP server URL')
    call_parser.add_argument('-t', '--tool', required=True, help='Tool name')
    call_parser.add_argument('-p', '--params', required=True, help='JSON parameters')
    
    # Call stdio command
    stdio_parser = subparsers.add_parser('call-stdio', help='Call tool via stdio')
    stdio_parser.add_argument('-s', '--server', required=True, help='Server name (email, linkedin)')
    stdio_parser.add_argument('-t', '--tool', required=True, help='Tool name')
    stdio_parser.add_argument('-p', '--params', required=True, help='JSON parameters')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_tools(args.url)
    
    elif args.command == 'call':
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON parameters: {e}")
            sys.exit(1)
        call_tool(args.url, args.tool, params)
    
    elif args.command == 'call-stdio':
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON parameters: {e}")
            sys.exit(1)
        call_tool_stdio(args.server, args.tool, params)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
