import subprocess

def StopMcpServer(self, server_name: str) -> bool:
    """
    Stop an MCP server process.
    
    Args:
        self: Orchestrator instance
        server_name: Name of the MCP server to stop
    
    Returns:
        True if successful, False otherwise
    """
    if server_name not in self.mcp_processes:
        self.logger.warning(f"MCP server {server_name} not running")
        return False

    try:
        proc = self.mcp_processes[server_name]
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        del self.mcp_processes[server_name]
        self.logger.info(f"Stopped {server_name} MCP server")
        return True
    except Exception as e:
        self.logger.error(f"Error stopping {server_name} MCP server: {e}")
        return True
