import subprocess
import sys
from pathlib import Path

def StartMcpServer(self, server_name: str) -> bool:
    """
    Start an MCP server process.
    
    Args:
        self: Orchestrator instance
        server_name: Name of the MCP server to start
    
    Returns:
        True if successful, False otherwise
    """
    mcp_servers = {
        'email': 'mcp-servers/email/server.py',
        'linkedin': 'mcp-servers/linkedin/server.py'
    }

    if server_name not in mcp_servers:
        self.logger.error(f"Unknown MCP server: {server_name}")
        return False

    server_path = Path(__file__).parent.parent.parent / mcp_servers[server_name]

    if not server_path.exists():
        self.logger.error(f"MCP server not found: {server_path}")
        return False

    try:
        # Start MCP server with stdio transport (for qwen code integration)
        cmd = ['uv', 'run', 'python', str(server_path)]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
        )

        self.mcp_processes[server_name] = proc
        self.logger.info(f"Started {server_name} MCP server (PID: {proc.pid})")

        return True

    except Exception as e:
        self.logger.error(f"Failed to start {server_name} MCP server: {e}")
        return False
