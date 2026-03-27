import sys
import subprocess
import time
from datetime import datetime
from typing import Any, Dict

def RalphLoop(self, prompt: str, completion_promise: str = "TASK_COMPLETE") -> None:
    """
    Run the Ralph Wiggum persistence loop.
    
    Args:
        self: Orchestrator instance
        prompt: Initial prompt for qwen code
        completion_promise: String to look for indicating task completion
    """
    self.logger.info("Starting Ralph Wiggum loop...")
    self.logger.info(f"Prompt: {prompt[:100]}...")
    self.logger.info(f"Max iterations: {self.max_iterations}")

    iteration = 0
    state_file = self.plans / f'RALPH_STATE_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'

    state: Dict[str, Any] = {
        'prompt': prompt,
        'iteration': 0,
        'started': datetime.now().isoformat(),
        'last_output': '',
        'completed': False
    }

    while iteration < self.max_iterations:
        iteration += 1
        state['iteration'] = iteration

        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"Iteration {iteration}/{self.max_iterations}")
        self.logger.info(f"{'='*50}")

        # Check completion criteria
        needs_action_count = self._count_files(self.needs_action)

        if needs_action_count == 0:
            self.logger.info("✓ All files processed - completion detected!")
            state['completed'] = True
            break

        # Build prompt with context
        full_prompt = f"""{prompt}

---
CONTEXT (Iteration {iteration}):
- Files remaining in /Needs_Action: {needs_action_count}

Continue processing. If task is complete, output: <promise>{completion_promise}</promise>
"""

        # Run qwen code
        try:
            qwen_exec = self._find_qwen_executable()
            if not qwen_exec:
                self.logger.error("qwen code not found, skipping iteration")
                break

            # Use positional prompt syntax (new CLI)
            full_prompt_text = f"First navigate to {str(self.vault_path)} and then: {full_prompt}"
            cmd = [qwen_exec, full_prompt_text]

            self.logger.info(f"Running qwen code (iteration {iteration})...")

            if not self.dry_run:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
                )

                output = result.stdout + result.stderr
                state['last_output'] = output[-1000:] if len(output) > 1000 else output

                # Check for completion promise
                if f'<promise>{completion_promise}</promise>' in output:
                    self.logger.info(f"Completion promise detected!")
                    state['completed'] = True
                    break

            else:
                self.logger.info("[DRY RUN] Would run qwen code")
                state['last_output'] = "Dry run - no output"

        except subprocess.TimeoutExpired:
            self.logger.warning("qwen code timed out, retrying...")
            state['last_output'] = "Timeout - retrying"
        except Exception as e:
            self.logger.error(f"Error running qwen code: {e}")
            state['last_output'] = f"Error: {e}"

        # Save state
        if not self.dry_run:
            state_content = f"""---
type: ralph_state
iteration: {iteration}
max_iterations: {self.max_iterations}
started: {state['started']}
completed: {state['completed']}
---

# Ralph Wiggum Loop State

## Prompt
{prompt}

## Last Output
{state['last_output']}

## Status

Iteration {iteration}/{self.max_iterations}
"""
            state_file.write_text(state_content, encoding='utf-8')

        # Brief pause between iterations
        time.sleep(2)

    # Final status
    self.logger.info(f"\n{'='*50}")
    if state['completed']:
        self.logger.info("Ralph loop completed successfully!")
    else:
        self.logger.warning(f"⚠️ Ralph loop ended after {iteration} iterations (max reached)")
    self.logger.info(f"{'='*50}")
