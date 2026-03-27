import subprocess

def StopWatcher(self, watcher_name: str) -> bool:
    """
    Stop a watcher process.
    
    Args:
        self: Orchestrator instance
        watcher_name: Name of the watcher to stop
    
    Returns:
        True if successful, False otherwise
    """
    if watcher_name not in self.watcher_processes:
        self.logger.warning(f"Watcher {watcher_name} not running")
        return False

    try:
        proc = self.watcher_processes[watcher_name]
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        del self.watcher_processes[watcher_name]
        self.logger.info(f"Stopped {watcher_name} watcher")
        return True
    except Exception as e:
        self.logger.error(f"Error stopping {watcher_name} watcher: {e}")
        return True
