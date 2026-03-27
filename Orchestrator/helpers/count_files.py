from pathlib import Path

def CountFiles(self, folder: Path) -> int:
    """
    Count markdown files in a folder.
    
    Args:
        self: Orchestrator instance
        folder: Path to folder to count files in
    
    Returns:
        Number of markdown files found
    """
    if not folder.exists():
        return 0
    return len(list(folder.glob('*.md')))
