from pathlib import Path
from typing import List

def GetApprovedActions(self) -> List[Path]:
    """
    Get list of approved action files ready for execution.
    
    Args:
        self: Orchestrator instance
    
    Returns:
        List of paths to approved action files
    """
    if not self.approved.exists():
        return []
    return sorted(self.approved.glob('*.md'))
