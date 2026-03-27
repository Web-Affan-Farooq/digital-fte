import shutil
import sys
from pathlib import Path
from typing import Optional

def FindQwenExecutable(self) -> Optional[str]:
    """
    Find the qwen code executable path.
    
    Args:
        self: Orchestrator instance
    
    Returns:
        Path to qwen executable or None if not found
    """
    # Try to find qwen in PATH
    qwen_path = shutil.which('qwen')
    if qwen_path:
        self.logger.info(f"Found qwen code at: {qwen_path}")
        return qwen_path

    # On Windows, also check common locations
    if sys.platform.startswith('win'):
        # Check pnpm global location
        appdata_local = Path.home() / 'AppData' / 'Local'
        pnpm_qwen = appdata_local / 'pnpm' / 'qwen.CMD'
        if pnpm_qwen.exists():
            self.logger.info(f"Found qwen code at pnpm location: {pnpm_qwen}")
            return str(pnpm_qwen)

        # Check npm global location
        appdata_roaming = Path.home() / 'AppData' / 'Roaming'
        npm_qwen = appdata_roaming / 'npm' / 'qwen.cmd'
        if npm_qwen.exists():
            self.logger.info(f"Found qwen code at npm location: {npm_qwen}")
            return str(npm_qwen)

    self.logger.warning("qwen code executable not found in PATH or common locations")
    return None
