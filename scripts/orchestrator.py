"""
Orchestrator for Digital FTE - Silver Tier

This script coordinates all watchers, MCP servers, qwen code processing,
and implements the Ralph Wiggum persistence loop for autonomous operation.

Features:
- Start/stop all watchers (Gmail, WhatsApp, Filesystem)
- Start/stop MCP servers (Email, LinkedIn)
- Trigger qwen code processing on demand
- Ralph Wiggum loop for multi-step task completion
- Dashboard updates
- Approval workflow execution
- Health monitoring

Usage:
    # Start all watchers
    uv run python scripts/orchestrator.py start

    # Start MCP servers
    uv run python scripts/orchestrator.py start-mcp

    # Process Needs_Action folder with qwen
    uv run python scripts/orchestrator.py process

    # Process approved actions
    uv run python scripts/orchestrator.py process-approvals

    # Start Ralph Wiggum loop
    uv run python scripts/orchestrator.py ralph-loop "Process all files"

    # Check system status
    uv run python scripts/orchestrator.py status

Environment Variables:
    VAULT_PATH: Path to Obsidian vault (default: ./vault)
    DRY_RUN: Set to 'false' to enable actual processing
    MAX_ITERATIONS: Max Ralph loop iterations (default: 10)
"""

import argparse
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from rich import print

dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class Orchestrator:
    """
    Main orchestrator for the Digital FTE system.

    Coordinates watchers, MCP servers, qwen code processing, and system health.
    """

    def __init__(
        self,
        vault_path: Optional[str] = None,
        max_iterations: int = 10,
        dry_run: bool = True
    ):
        """
        Initialize the orchestrator.

        Args:
            vault_path: Path to the Obsidian vault
            max_iterations: Maximum iterations for Ralph loop
            dry_run: Enable dry run mode
        """
        # Get vault path from args or environment
        self.vault_path = Path(vault_path) if vault_path else Path(os.getenv('VAULT_PATH', './vault'))
        self.max_iterations = max_iterations
        self.dry_run = dry_run

        # Ensure vault exists
        if not self.vault_path.exists():
            print(f"❌ Vault path does not exist: {self.vault_path}")
            sys.exit(1)

        # Folder paths
        self.inbox = self.vault_path / 'Inbox'
        self.needs_action = self.vault_path / 'Needs_Action'
        self.in_progress = self.vault_path / 'In_Progress'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.approved = self.vault_path / 'Approved'
        self.done = self.vault_path / 'Done'
        self.plans = self.vault_path / 'Plans'
        self.briefings = self.vault_path / 'Briefings'
        self.logs = self.vault_path / 'Logs'
        self.dashboard = self.vault_path / 'Dashboard.md'

        # Ensure all folders exist
        self._ensure_directories()

        # Process tracking
        self.watcher_processes: Dict[str, subprocess.Popen] = {}
        self.mcp_processes: Dict[str, subprocess.Popen] = {}

        # Setup logging
        self.logger = self._setup_logging()

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for folder in [
            self.inbox, self.needs_action, self.in_progress,
            self.pending_approval, self.approved, self.done,
            self.plans, self.briefings, self.logs
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> logging.Logger:
        """Configure logging for the orchestrator."""
        logger = logging.getLogger('Orchestrator')
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # File handler
        log_file = self.logs / f'orchestrator_{datetime.now().strftime("%Y-%m-%d")}.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Avoid duplicate handlers
        if not logger.handlers:
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)

        return logger

    def _count_files(self, folder: Path) -> int:
        """Count markdown files in a folder."""
        if not folder.exists():
            return 0
        return len(list(folder.glob('*.md')))

    def _find_qwen_executable(self) -> Optional[str]:
        """
        Find the qwen code executable path.

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

    def update_dashboard(self) -> None:
        """Update the Dashboard.md with current system status."""
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
            import re
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

    def start_watcher(self, watcher_name: str) -> bool:
        """Start a watcher process."""
        watcher_scripts = {
            'gmail': 'gmail_watcher.py',
            'filesystem': 'filesystem_watcher.py',
            'whatsapp': 'whatsapp_watcher.py'
        }

        if watcher_name not in watcher_scripts:
            self.logger.error(f"Unknown watcher: {watcher_name}")
            return False

        script_path = Path(__file__).parent / watcher_scripts[watcher_name]

        if not script_path.exists():
            self.logger.error(f"Watcher script not found: {script_path}")
            return False

        try:
            # Start watcher as background process using uv
            cmd = [
                'uv', 'run', 'python', str(script_path),
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

        except Exception as e:
            self.logger.error(f"Failed to start {watcher_name} watcher: {e}")
            return False

    def stop_watcher(self, watcher_name: str) -> bool:
        """Stop a watcher process."""
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

    def start_mcp_server(self, server_name: str) -> bool:
        """Start an MCP server process."""
        mcp_servers = {
            'email': 'mcp-servers/email/server.py',
            'linkedin': 'mcp-servers/linkedin/server.py'
        }

        if server_name not in mcp_servers:
            self.logger.error(f"Unknown MCP server: {server_name}")
            return False

        server_path = Path(__file__).parent.parent / mcp_servers[server_name]
        
        if not server_path.exists():
            self.logger.error(f"MCP server not found: {server_path}")
            return False

        try:
            # Start MCP server with stdio transport (for qwen code integration)
            cmd = ['uv', 'run', 'python', str(server_path)]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
            )

            self.mcp_processes[server_name] = proc
            self.logger.info(f"Started {server_name} MCP server (PID: {proc.pid})")

            return True

        except Exception as e:
            self.logger.error(f"Failed to start {server_name} MCP server: {e}")
            return False

    def stop_mcp_server(self, server_name: str) -> bool:
        """Stop an MCP server process."""
        if server_name not in self.mcp_processes:
            self.logger.warning(f"MCP server {server_name} not running")
            return False

        try:
            proc = self.mcp_processes[server_name]
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            del self.mcp_processes[server_name]
            self.logger.info(f"Stopped {server_name} MCP server")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping {server_name} MCP server: {e}")
            return True

    def start_all_watchers(self) -> None:
        """Start all configured watchers."""
        self.logger.info("Starting all watchers...")

        # Start Gmail watcher (if credentials available)
        gmail_creds = Path.home() / '.gmail_watcher' / 'credentials.json'
        if gmail_creds.exists():
            self.start_watcher('gmail')
        else:
            self.logger.info("Gmail credentials not configured, skipping Gmail watcher")

        # Start filesystem watcher
        self.start_watcher('filesystem')

        # Start WhatsApp watcher (if Playwright available)
        try:
            from playwright.sync_api import sync_playwright
            self.start_watcher('whatsapp')
        except ImportError:
            self.logger.info("Playwright not available, skipping WhatsApp watcher")

        # Update dashboard
        self.update_dashboard()

        self.logger.info(f"Started {len(self.watcher_processes)} watcher(s)")

    def stop_all_watchers(self) -> None:
        """Stop all running watchers."""
        self.logger.info("Stopping all watchers...")

        for watcher_name in list(self.watcher_processes.keys()):
            self.stop_watcher(watcher_name)

        self.update_dashboard()
        self.logger.info("All watchers stopped")

    def start_all_mcp_servers(self) -> None:
        """Start all MCP servers."""
        self.logger.info("Starting all MCP servers...")

        # Start Email MCP server
        self.start_mcp_server('email')

        # Start LinkedIn MCP server
        self.start_mcp_server('linkedin')

        self.logger.info(f"Started {len(self.mcp_processes)} MCP server(s)")

    def stop_all_mcp_servers(self) -> None:
        """Stop all MCP servers."""
        self.logger.info("Stopping all MCP servers...")

        for server_name in list(self.mcp_processes.keys()):
            self.stop_mcp_server(server_name)

        self.logger.info("All MCP servers stopped")

    def get_approved_actions(self) -> List[Path]:
        """Get list of approved action files ready for execution."""
        if not self.approved.exists():
            return []
        return sorted(self.approved.glob('*.md'))

    def process_approved_action(self, filepath: Path) -> bool:
        """
        Process an approved action file by calling the appropriate MCP server.

        Args:
            filepath: Path to approved action file

        Returns:
            True if processed successfully
        """
        try:
            content = filepath.read_text(encoding='utf-8')

            # Parse frontmatter
            import re
            frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                self.logger.warning(f"No frontmatter found in {filepath}")
                return False

            frontmatter = frontmatter_match.group(1)
            metadata = {}
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()

            action_type = metadata.get('type', '')

            # Route to appropriate MCP server
            if 'email' in action_type.lower():
                return self._execute_email_action(filepath, metadata, content)
            elif 'linkedin' in action_type.lower():
                return self._execute_linkedin_action(filepath, metadata, content)
            else:
                self.logger.warning(f"Unknown action type: {action_type}")
                return False

        except Exception as e:
            self.logger.error(f"Error processing approved action: {e}")
            return False

    def _execute_email_action(self, filepath: Path, metadata: Dict, content: str) -> bool:
        """Execute an email action using the Email MCP server."""
        # For now, log the action
        self.logger.info(f"Executing email action: {filepath.name}")

        # In production, this would call the MCP server via HTTP or stdio
        # Example using httpx:
        # import httpx
        # response = httpx.post('http://localhost:8801/send_email', json={...})

        # Move to Done folder
        done_path = self.done / filepath.name
        if not self.dry_run:
            filepath.rename(done_path)

        self.logger.info(f"Email action completed: {filepath.name} -> {done_path.name}")
        return True

    def _execute_linkedin_action(self, filepath: Path, metadata: Dict, content: str) -> bool:
        """Execute a LinkedIn action using the LinkedIn MCP server."""
        self.logger.info(f"Executing LinkedIn action: {filepath.name}")

        # Extract content from markdown
        content_match = content.search(r'## Content\n\n(.*?)\n---', content, content.DOTALL)
        if content_match:
            post_content = content_match.group(1)
            self.logger.info(f"LinkedIn post content: {post_content[:100]}...")

        # In production, call the MCP server
        # For now, just log and move to Done

        done_path = self.done / filepath.name
        if not self.dry_run:
            filepath.rename(done_path)

        self.logger.info(f"LinkedIn action completed: {filepath.name} -> {done_path.name}")
        return True

    def process_approvals(self) -> None:
        """Process all approved actions."""
        self.logger.info("Processing approved actions...")

        approved_files = self.get_approved_actions()

        if not approved_files:
            self.logger.info("No approved actions to process")
            return

        for filepath in approved_files:
            self.logger.info(f"Processing: {filepath.name}")
            success = self.process_approved_action(filepath)

            if success:
                self.logger.info(f"✓ Completed: {filepath.name}")
            else:
                self.logger.error(f"✗ Failed: {filepath.name}")

        self.logger.info(f"Processed {len(approved_files)} approved action(s)")

    def get_needs_action_files(self) -> List[Path]:
        """Get list of files in Needs_Action folder."""
        if not self.needs_action.exists():
            return []
        return sorted(self.needs_action.glob('*.md'))

    def trigger_qwen_processing(self, prompt: Optional[str] = None) -> bool:
        """Trigger qwen code to process the Needs_Action folder."""
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

    def ralph_loop(self, prompt: str, completion_promise: str = "TASK_COMPLETE") -> None:
        """Run the Ralph Wiggum persistence loop."""
        self.logger.info("Starting Ralph Wiggum loop...")
        self.logger.info(f"Prompt: {prompt[:100]}...")
        self.logger.info(f"Max iterations: {self.max_iterations}")

        iteration = 0
        state_file = self.plans / f'RALPH_STATE_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'

        state = {
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

    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            'vault_path': str(self.vault_path),
            'dry_run': self.dry_run,
            'watchers': {
                name: 'running' for name in self.watcher_processes
            },
            'mcp_servers': {
                name: 'running' for name in self.mcp_processes
            },
            'folders': {
                'inbox': self._count_files(self.inbox),
                'needs_action': self._count_files(self.needs_action),
                'in_progress': self._count_files(self.in_progress),
                'pending_approval': self._count_files(self.pending_approval),
                'approved': self._count_files(self.approved),
                'done': self._count_files(self.done),
            },
            'dashboard': 'exists' if self.dashboard.exists() else 'missing',
            'timestamp': datetime.now().isoformat()
        }

    def print_status(self) -> None:
        """Print current system status to console."""
        status = self.get_status()

        # Use ASCII-safe icons for Windows compatibility
        is_windows = sys.platform.startswith('win')
        if is_windows:
            icons = {
                'robot': '[FTE]',
                'vault': '[DIR]',
                'mode': '[MODE]',
                'time': '[TIME]',
                'chart': '[STATS]',
                'red': '[!]',
                'yellow': '[*]',
                'green': '[OK]',
                'server': '[MCP]',
                'watcher': '[W]'
            }
        else:
            icons = {
                'robot': '🤖',
                'vault': '📁',
                'mode': '🔧',
                'time': '⏰',
                'chart': '📊',
                'red': '🔴',
                'yellow': '🟡',
                'green': '🟢',
                'server': '🖥️',
                'watcher': '👁️'
            }

        print("\n" + "=" * 60)
        print(f"{icons['robot']} Digital FTE Status - Silver Tier")
        print("=" * 60)
        print(f"\n{icons['vault']} Vault: {status['vault_path']}")
        print(f"{icons['mode']} Mode: {'Dry Run' if status['dry_run'] else 'Production'}")
        print(f"{icons['time']} Updated: {status['timestamp']}")

        print(f"\n{icons['chart']} Folder Status:")
        for folder, count in status['folders'].items():
            icon = icons['red'] if count > 5 else icons['yellow'] if count > 0 else icons['green']
            print(f"  {icon} /{folder}: {count} files")

        print(f"\n{icons['watcher']} Watchers:")
        if status['watchers']:
            for watcher, state in status['watchers'].items():
                icon = icons['green'] if state == 'running' else icons['watcher']
                print(f"  {icon} {watcher}: {state}")
        else:
            print("  (none running)")

        print(f"\n{icons['server']} MCP Servers:")
        if status['mcp_servers']:
            for server, state in status['mcp_servers'].items():
                icon = icons['green'] if state == 'running' else icons['server']
                print(f"  {icon} {server}: {state}")
        else:
            print("  (none running)")

        print("\n" + "=" * 60 + "\n")


def main():
    """Main entry point for orchestrator."""
    parser = argparse.ArgumentParser(description='Digital FTE Orchestrator - Silver Tier')
    parser.add_argument(
        'command',
        nargs='?',
        choices=['start', 'stop', 'start-mcp', 'stop-mcp', 'process', 'process-approvals', 'ralph-loop', 'status'],
        help='Command to run'
    )
    parser.add_argument(
        '--vault',
        type=str,
        default=os.getenv('VAULT_PATH', './vault'),
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--watchers',
        nargs='+',
        default=['filesystem', 'whatsapp'],
        help='Watchers to start'
    )
    parser.add_argument(
        '--prompt',
        type=str,
        help='Custom prompt for qwen    processing'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=int(os.getenv('MAX_ITERATIONS', '10')),
        help='Max Ralph loop iterations'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=dry_run,
        help='Enable dry run mode'
    )

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = Orchestrator(
        vault_path=args.vault,
        max_iterations=args.max_iterations,
        dry_run=args.dry_run
    )

    # Handle commands
    if args.command == 'start':
        print("🚀 Starting Digital FTE Silver Tier...\n")
        for watcher in args.watchers:
            orchestrator.start_watcher(watcher)
        orchestrator.print_status()
        print("\nWatchers started. Press Ctrl+C to stop.")

        # Keep running
        try:
            while True:
                time.sleep(60)
                orchestrator.update_dashboard()
        except KeyboardInterrupt:
            print("\n\n👋 Stopping watchers...")
            orchestrator.stop_all_watchers()

    elif args.command == 'stop':
        print("🛑 Stopping Digital FTE...\n")
        orchestrator.stop_all_watchers()
        orchestrator.stop_all_mcp_servers()
        orchestrator.print_status()

    elif args.command == 'start-mcp':
        print("🖥️  Starting MCP servers...\n")
        orchestrator.start_all_mcp_servers()
        orchestrator.print_status()

    elif args.command == 'stop-mcp':
        print("⏹️  Stopping MCP servers...\n")
        orchestrator.stop_all_mcp_servers()
        orchestrator.print_status()

    elif args.command == 'process':
        print("🧠 Triggering qwen code  processing...\n")
        success = orchestrator.trigger_qwen_processing(args.prompt)
        if success:
            print("✅ Processing started")
        else:
            print("❌ Processing failed")
            sys.exit(1)

    elif args.command == 'process-approvals':
        print("⚡ Processing approved actions...\n")
        orchestrator.process_approvals()
        print("✅ Approval processing complete")

    elif args.command == 'ralph-loop':
        prompt = args.prompt or "Process all files in /Needs_Action folder"
        print(f"🔄 Starting Ralph Wiggum loop...\n")
        print(f"Prompt: {prompt}\n")
        orchestrator.ralph_loop(prompt)

    elif args.command == 'status' or args.command is None:
        orchestrator.print_status()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
