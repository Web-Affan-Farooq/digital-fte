import re
from datetime import datetime

def UpdateDashboard(self) -> None:
    """
    Update the Dashboard.md with current system status.
    
    Args:
        self: Orchestrator instance
    """
    try:
        if not self.dashboard.exists():
            self.logger.warning(f"Dashboard not found: {self.dashboard}")
            return

        # Count files in each folder
        counts = {
            'inbox': self._count_files(self.inbox),
            'needs_action': self._count_files(self.needs_action),
            'in_progress': self._count_files(self.in_progress),
            'pending_approval': self._count_files(self.pending_approval),
            'approved': self._count_files(self.approved),
            'done': self._count_files(self.done),
        }

        # Calculate totals
        total_pending = counts['needs_action'] + counts['pending_approval']
        total_done = counts['done']

        # Get system status
        watchers_running = len(self.watcher_processes)
        mcp_running = len(self.mcp_processes)
        system_status = "🟢 Operational" if (watchers_running > 0 or mcp_running > 0) else "🟡 Idle"

        # Read current dashboard
        content = self.dashboard.read_text(encoding='utf-8')

        # Update timestamp
        content = re.sub(
            r'last_updated:.*',
            f'last_updated: {datetime.now().isoformat()}',
            content
        )

        # Write updated dashboard
        if not self.dry_run:
            self.dashboard.write_text(content, encoding='utf-8')

        self.logger.info(f"Dashboard updated: {total_pending} pending, {total_done} done")

    except Exception as e:
        self.logger.error(f"Error updating dashboard: {e}")
