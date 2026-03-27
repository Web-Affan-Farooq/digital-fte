from datetime import datetime

from typing import Any, Dict
def GetStatus(self) -> Dict[str, Any]:
    """
    Get current system status.
    
    Args:
        self: Orchestrator instance
    
    Returns:
        Dictionary containing system status information
    """
    return {
        'vault_path': str(self.vault_path),
        'dry_run': self.dry_run,
        'watchers': {
            name: 'running' for name in self.watcher_processes
        },
        'mcp_servers': {
            name: 'running' for name in self.mcp_processes
        },
        'folders': {
            'inbox': self._count_files(self.inbox),
            'needs_action': self._count_files(self.needs_action),
            'in_progress': self._count_files(self.in_progress),
            'pending_approval': self._count_files(self.pending_approval),
            'approved': self._count_files(self.approved),
            'done': self._count_files(self.done),
        },
        'dashboard': 'exists' if self.dashboard.exists() else 'missing',
        'timestamp': datetime.now().isoformat()
    }
