import subprocess
import sys
from pathlib import Path

def StartWatcher(self, watcher_name: str) -> bool:
    """
    Start a watcher process.
    
    Args:
        self: Orchestrator instance
        watcher_name: Name of the watcher to start
    
    Returns:
        True if successful, False otherwise
    """
    watcher_scripts = {
        'gmail': 'GmailWatcher.main',
        'filesystem': 'FilesystemWatcher.main',
        'whatsapp': 'WhatsappWatcher.main'
    }

    if watcher_name not in watcher_scripts:
        self.logger.error(f"Unknown watcher: {watcher_name}")
        return False
# Path(__file__).parent.parent / 
    script_path = watcher_scripts[watcher_name]

    try:
        # Start watcher as background process using uv
        cmd = [
            'uv', 'run', 'python','-m', str(script_path),
            '--vault', str(self.vault_path)
        ]

        # Add dry run flag if enabled
        if self.dry_run:
            cmd.append('--dry-run')

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
        )

        self.watcher_processes[watcher_name] = proc
        self.logger.info(f"Started {watcher_name} watcher (PID: {proc.pid})")

        return True
    
    except FileNotFoundError: 
        self.logger.error(f"Watcher script not found: {script_path}")
        return False
    except Exception as e:
        self.logger.error(f"Failed to start {watcher_name} watcher: {e}")
        return False
