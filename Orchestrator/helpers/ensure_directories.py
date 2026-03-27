def EnsureDirectories(self) -> None:
    """
    Create necessary directories if they don't exist.
    
    Args:
        self: Orchestrator instance
    """
    for folder in [
        self.inbox, self.needs_action, self.in_progress,
        self.pending_approval, self.approved, self.done,
        self.plans, self.briefings, self.logs
    ]:
        folder.mkdir(parents=True, exist_ok=True)
