import subprocess
import sys
from typing import Optional

def TriggerQwenProcessing(self, prompt: Optional[str] = None) -> bool:
    """
    Trigger qwen code to process the Needs_Action folder.
    
    Args:
        self: Orchestrator instance
        prompt: Optional custom prompt for qwen code
    
    Returns:
        True if processing started successfully
    """
    # Find qwen executable
    qwen_exec = self._find_qwen_executable()
    if not qwen_exec:
        self.logger.error("qwen code not found. Install with: npm install -g @anthropic/qwen-code")
        return False

    # Check if qwen code is available
    try:
        result = subprocess.run(
            [qwen_exec, '--version'],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
        )
        self.logger.info(f"qwen code version: {result.stdout.strip()}")
        if result.returncode != 0:
            self.logger.error("qwen code not available or responding")
            return False
    except FileNotFoundError:
        self.logger.error("qwen code not found. Install with: npm install -g @anthropic/qwen-code")
        return False
    except subprocess.TimeoutExpired:
        self.logger.error("qwen code version check timed out")
        return False

    # Default prompt
    if not prompt:
        needs_action_count = self._count_files(self.needs_action)
        pending_count = self._count_files(self.pending_approval)

        prompt = f"""Process the Digital FTE vault at {self.vault_path}.

Current status:
- Files in /Needs_Action: {needs_action_count}
- Files in /Pending_Approval: {pending_count}

Instructions:
1. Read all files in /Needs_Action folder
2. For each file, determine the required action based on Company_Handbook.md rules
3. Create plans in /Plans folder for complex tasks
4. For sensitive actions (payments, emails, LinkedIn posts), create approval requests in /Pending_Approval
5. Move processed files to /Done folder
6. Update Dashboard.md with activity summary

Follow the Rules of Engagement in Company_Handbook.md at all times."""

    self.logger.info(f"Triggering qwen code processing...")

    # Run qwen code with positional prompt (new CLI syntax)
    # Qwen Code now uses: qwen [query..] for positional prompts
    # Or: qwen -p "prompt" for --prompt flag (but not both)
    full_prompt = f"Navigate to {str(self.vault_path)} and then: {prompt}"

    cmd = [qwen_exec, full_prompt]

    try:
        self.logger.info(f"Running: {cmd[0]} [prompt]...")

        if not self.dry_run:
            subprocess.run(cmd, timeout=300)

        return True

    except subprocess.TimeoutExpired:
        self.logger.error("qwen code processing timed out")
        return False
    except Exception as e:
        self.logger.error(f"Error triggering qwen code: {e}")
        return False
