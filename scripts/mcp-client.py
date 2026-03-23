"""
MCP Client for Digital FTE

Helper script to call MCP server tools via HTTP or stdio.
Uses FastMCP client for proper MCP protocol handling.

Usage:
    # List available tools
    uv run python scripts/mcp-client.py list --url http://localhost:8801/mcp

    # Call a tool
uv run python scripts/mcp-client.py call ^
  --url http://localhost:8801/mcp ^
  -t send_email ^
  -p "{\"to\": \"affanfarooq824@gmail.com\", \"subject\": \"Test email\", \"body\": \"Hello affan\"}"

  # List tools
  

    # Call via stdio (for local MCP servers)
    uv run python scripts/mcp-client.py call-stdio -s email -t send_email -p '{"to": "test@example.com"}'
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport, SSETransport
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    print("fastmcp not installed. Install with: uv add fastmcp")


def get_transport(url: str):
    """Get appropriate transport for the URL."""
    # Try StreamableHttpTransport first (default for FastMCP 3.x)
    try:
        return StreamableHttpTransport(url=url)
    except Exception:
        # Fallback to SSE transport for older servers
        return SSETransport(url=url)


async def list_tools_async(server_url: str) -> None:
    """List available tools from MCP server (async)."""
    if not FASTMCP_AVAILABLE:
        print("fastmcp not available")
        return

    try:
        transport = get_transport(server_url)
        client = Client(transport)
        
        async with client:
            tools = await client.list_tools()
            
            print(f"\nAvailable tools from {server_url}:\n")
            print("-" * 60)

            for tool in tools:
                print(f"\n{tool.name}")
                print(f"  Description: {tool.description or 'No description'}")
                if tool.inputSchema and 'properties' in tool.inputSchema:
                    schema = tool.inputSchema
                    print("  Parameters:")
                    for param, details in schema['properties'].items():
                        required = param in schema.get('required', [])
                        desc = details.get('description', '') if isinstance(details, dict) else ''
                        print(f"    - {param} {'(required)' if required else '(optional)'}: {desc}")

            print("\n" + "-" * 60)

    except Exception as e:
        print(f"Error: {e}")
        print(f"Make sure the MCP server is running at {server_url}")


async def call_tool_async(server_url: str, tool_name: str, params: dict) -> None:
    """Call a tool on MCP server (async)."""
    if not FASTMCP_AVAILABLE:
        print("fastmcp not available")
        return

    try:
        transport = get_transport(server_url)
        client = Client(transport)
        
        async with client:
            result = await client.call_tool(tool_name, params)
            
            print(f"\nTool: {tool_name}")
            print(f"Result: {result}")

    except Exception as e:
        print(f"Error: {e}")
        print(f"Make sure the MCP server is running at {server_url}")


def list_tools(server_url: str) -> None:
    """List available tools from MCP server."""
    import asyncio
    asyncio.run(list_tools_async(server_url))


def call_tool(server_url: str, tool_name: str, params: dict) -> None:
    """Call a tool on MCP server."""
    import asyncio
    asyncio.run(call_tool_async(server_url, tool_name, params))


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
