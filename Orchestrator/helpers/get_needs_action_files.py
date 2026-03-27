from pathlib import Path
from typing import List

def GetNeedsActionFiles(self) -> List[Path]:
    """
    Get list of files in Needs_Action folder.
    
    Args:
        self: Orchestrator instance
    
    Returns:
        List of paths to files in Needs_Action folder
    """
    if not self.needs_action.exists():
        return []
    return sorted(self.needs_action.glob('*.md'))
