"""
Orchestrator for Digital FTE

This script coordinates all watchers, triggers Claude Code processing,
and implements the Ralph Wiggum persistence loop for autonomous operation.

Features:
- Start/stop all watchers
- Trigger Claude Code processing on demand
- Ralph Wiggum loop for multi-step task completion
- Dashboard updates
- Health monitoring

Usage:
    # Start all watchers
    python scripts/orchestrator.py start
    
    # Process Needs_Action folder with Claude
    python scripts/orchestrator.py process
    
    # Start Ralph Wiggum loop
    python scripts/orchestrator.py ralph-loop "Process all files"
    
    # Check system status
    python scripts/orchestrator.py --status
    
Environment Variables:
    VAULT_PATH: Path to Obsidian vault (default: ./vault)
    DRY_RUN: Set to 'false' to enable actual processing
    MAX_ITERATIONS: Max Ralph loop iterations (default: 10)
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class Orchestrator:
    """
    Main orchestrator for the Digital FTE system.
    
    Coordinates watchers, Claude Code processing, and system health.
    
    Attributes:
        vault_path: Path to the Obsidian vault
        processes: Dictionary of running watcher processes
        max_iterations: Maximum Ralph loop iterations
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
        self.processes: Dict[str, subprocess.Popen] = {}
        self.pid_file = Path(tempfile.gettempdir()) / 'digital_fte_orchestrator.pid'
        
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
        """
        Configure logging for the orchestrator.
        
        Returns:
            Configured logger instance
        """
        import logging
        
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
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger

    def _count_files(self, folder: Path) -> int:
        """
        Count markdown files in a folder.
        
        Args:
            folder: Path to folder
            
        Returns:
            Number of .md files
        """
        if not folder.exists():
            return 0
        return len(list(folder.glob('*.md')))

    def update_dashboard(self) -> None:
        """
        Update the Dashboard.md with current system status.
        """
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
            watchers_running = len(self.processes)
            system_status = "🟢 Operational" if watchers_running > 0 else "🟡 Idle"
            
            # Read current dashboard
            content = self.dashboard.read_text(encoding='utf-8')
            
            # Update status section
            import re
            
            # Update counts
            status_lines = [
                f"| `/Inbox` | {counts['inbox']} | - |",
                f"| `/Needs_Action` | {counts['needs_action']} | {'⚠️ Review' if counts['needs_action'] > 0 else '-'} |",
                f"| `/In_Progress` | {counts['in_progress']} | - |",
                f"| `/Pending_Approval` | {counts['pending_approval']} | {'🔴 Review Required' if counts['pending_approval'] > 0 else '-'} |",
            ]
            
            # Update today's completed count
            today = datetime.now().strftime('%Y-%m-%d')
            done_today = 0  # Could count files modified today
            
            # Write updates
            content = re.sub(
                r'\| System Status \|.*?\|',
                f'| **System Status** | {system_status} | {"Normal" if watchers_running > 0 else "No watchers"} |',
                content,
                flags=re.DOTALL
            )
            
            content = re.sub(
                r'\| Pending Actions \|.*?\|',
                f'| **Pending Actions** | {total_pending} | {"⚠️ Action needed" if total_pending > 0 else "-"} |',
                content,
                flags=re.DOTALL
            )
            
            content = re.sub(
                r'\| Tasks Completed Today \|.*?\|',
                f'| **Tasks Completed Today** | {done_today} | - |',
                content,
                flags=re.DOTALL
            )
            
            # Update folder counts
            for i, line in enumerate(content.split('\n')):
                if '`/Inbox`' in line and 'count' in line.lower():
                    content = content.replace(line, status_lines[0])
                elif '`/Needs_Action`' in line and 'count' in line.lower():
                    content = content.replace(line, status_lines[1])
                elif '`/Pending_Approval`' in line and 'count' in line.lower():
                    content = content.replace(line, status_lines[3])
            
            # Update timestamp
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
        """
        Start a watcher process.
        
        Args:
            watcher_name: Name of watcher ('gmail', 'filesystem')
            
        Returns:
            True if started successfully
        """
        watcher_scripts = {
            'gmail': 'gmail_watcher.py',
            'filesystem': 'filesystem_watcher.py'
        }
        
        if watcher_name not in watcher_scripts:
            self.logger.error(f"Unknown watcher: {watcher_name}")
            return False
        
        script_path = Path(__file__).parent / watcher_scripts[watcher_name]
        
        if not script_path.exists():
            self.logger.error(f"Watcher script not found: {script_path}")
            return False
        
        try:
            # Start watcher as background process
            cmd = [sys.executable, str(script_path), '--vault', str(self.vault_path)]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes[watcher_name] = proc
            self.logger.info(f"Started {watcher_name} watcher (PID: {proc.pid})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start {watcher_name} watcher: {e}")
            return False

    def stop_watcher(self, watcher_name: str) -> bool:
        """
        Stop a watcher process.
        
        Args:
            watcher_name: Name of watcher to stop
            
        Returns:
            True if stopped successfully
        """
        if watcher_name not in self.processes:
            self.logger.warning(f"Watcher {watcher_name} not running")
            return False
        
        try:
            proc = self.processes[watcher_name]
            proc.terminate()
            proc.wait(timeout=5)
            del self.processes[watcher_name]
            self.logger.info(f"Stopped {watcher_name} watcher")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping {watcher_name} watcher: {e}")
            # Force kill
            proc.kill()
            return True

    def start_all_watchers(self) -> None:
        """
        Start all configured watchers.
        """
        self.logger.info("Starting all watchers...")
        
        # Start Gmail watcher (if credentials available)
        if os.getenv('GMAIL_CREDENTIALS_PATH'):
            self.start_watcher('gmail')
        else:
            self.logger.info("Gmail credentials not configured, skipping Gmail watcher")
        
        # Start filesystem watcher
        self.start_watcher('filesystem')
        
        # Update dashboard
        self.update_dashboard()
        
        self.logger.info(f"Started {len(self.processes)} watcher(s)")

    def stop_all_watchers(self) -> None:
        """
        Stop all running watchers.
        """
        self.logger.info("Stopping all watchers...")
        
        for watcher_name in list(self.processes.keys()):
            self.stop_watcher(watcher_name)
        
        self.update_dashboard()
        self.logger.info("All watchers stopped")

    def get_needs_action_files(self) -> List[Path]:
        """
        Get list of files in Needs_Action folder.
        
        Returns:
            List of markdown file paths
        """
        if not self.needs_action.exists():
            return []
        return sorted(self.needs_action.glob('*.md'))

    def get_pending_approvals(self) -> List[Path]:
        """
        Get list of files in Pending_Approval folder.
        
        Returns:
            List of markdown file paths
        """
        if not self.pending_approval.exists():
            return []
        return sorted(self.pending_approval.glob('*.md'))

    def trigger_claude_processing(self, prompt: Optional[str] = None) -> bool:
        """
        Trigger Claude Code to process the Needs_Action folder.
        
        Args:
            prompt: Custom prompt for Claude (optional)
            
        Returns:
            True if processing started successfully
        """
        # Check if Claude Code is available
        try:
            result = subprocess.run(
                ['claude', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                self.logger.error("Claude Code not available or not responding")
                return False
        except FileNotFoundError:
            self.logger.error("Claude Code not found. Install with: npm install -g @anthropic/claude-code")
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("Claude Code version check timed out")
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
4. For sensitive actions (payments, emails), create approval requests in /Pending_Approval
5. Move processed files to /Done folder
6. Update Dashboard.md with activity summary

Follow the Rules of Engagement in Company_Handbook.md at all times."""
        
        # Create a state file for Ralph loop
        state_file = self.plans / f'CLAUDE_STATE_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        state_content = f"""---
type: claude_state
created: {datetime.now().isoformat()}
status: processing
iteration: 1
max_iterations: {self.max_iterations}
---

# Claude Processing State

## Prompt
{prompt}

## Status
Processing started at {datetime.now().isoformat()}

## Completion Criteria
Task is complete when:
- All files in /Needs_Action have been processed
- Approval requests created for sensitive actions
- Dashboard.md updated with summary
- Processed files moved to /Done

"""
        
        if not self.dry_run:
            state_file.write_text(state_content, encoding='utf-8')
        
        self.logger.info(f"Triggering Claude Code processing...")
        self.logger.info(f"State file: {state_file}")
        
        # Run Claude Code
        cmd = [
            'claude',
            '--prompt', prompt,
            '--cwd', str(self.vault_path)
        ]
        
        try:
            # For now, just log the command
            # In production, you'd run this and capture output
            self.logger.info(f"Would run: {' '.join(cmd)}")
            
            if not self.dry_run:
                # subprocess.run(cmd, timeout=300)  # 5 minute timeout
                pass
            
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Claude Code processing timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error triggering Claude Code: {e}")
            return False

    def ralph_loop(
        self,
        prompt: str,
        completion_promise: str = "TASK_COMPLETE",
        check_file_movement: bool = True
    ) -> None:
        """
        Run the Ralph Wiggum persistence loop.
        
        Keeps Claude working until tasks are complete by re-injecting
        prompts when Claude tries to exit prematurely.
        
        Args:
            prompt: Initial prompt for Claude
            completion_promise: String Claude outputs when complete
            check_file_movement: Also check if files moved to /Done
        """
        self.logger.info("Starting Ralph Wiggum loop...")
        self.logger.info(f"Prompt: {prompt[:100]}...")
        self.logger.info(f"Max iterations: {self.max_iterations}")
        
        iteration = 0
        state_file = self.plans / f'RALPH_STATE_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        
        # Initial state
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
            
            if check_file_movement and needs_action_count == 0:
                self.logger.info("✓ All files processed - completion detected!")
                state['completed'] = True
                break
            
            # Build prompt with context
            full_prompt = f"""{prompt}

---
CONTEXT (Iteration {iteration}):
- Files remaining in /Needs_Action: {needs_action_count}
- Previous output: {state.get('last_output', 'None')}

Continue processing. If task is complete, output: <promise>{completion_promise}</promise>
"""
            
            # Run Claude Code
            try:
                cmd = [
                    'claude',
                    '--prompt', full_prompt,
                    '--cwd', str(self.vault_path)
                ]
                
                self.logger.info(f"Running: {' '.join(cmd[:3])}...")
                
                if not self.dry_run:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    output = result.stdout + result.stderr
                    state['last_output'] = output[-1000:] if len(output) > 1000 else output
                    
                    # Check for completion promise
                    if f'<promise>{completion_promise}</promise>' in output:
                        self.logger.info(f"✓ Completion promise detected!")
                        state['completed'] = True
                        break
                    
                else:
                    self.logger.info("[DRY RUN] Would run Claude Code")
                    state['last_output'] = "Dry run - no output"
                    
            except subprocess.TimeoutExpired:
                self.logger.warning("Claude Code timed out, retrying...")
                state['last_output'] = "Timeout - retrying"
            except Exception as e:
                self.logger.error(f"Error running Claude Code: {e}")
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
            self.logger.info("✅ Ralph loop completed successfully!")
        else:
            self.logger.warning(f"⚠️ Ralph loop ended after {iteration} iterations (max reached)")
        self.logger.info(f"{'='*50}")
        
        # Update state file
        if not self.dry_run:
            state_content = f"""---
type: ralph_state
iteration: {iteration}
max_iterations: {self.max_iterations}
started: {state['started']}
completed: {state['completed']}
ended: {datetime.now().isoformat()}
---

# Ralph Wiggum Loop - Final State

## Result
{'✅ COMPLETED' if state['completed'] else '⚠️ MAX ITERATIONS REACHED'}

## Summary
- Iterations: {iteration}
- Started: {state['started']}
- Ended: {datetime.now().isoformat()}

## Original Prompt
{prompt}
"""
            state_file.write_text(state_content, encoding='utf-8')

    def get_status(self) -> Dict[str, Any]:
        """
        Get current system status.
        
        Returns:
            Dictionary of status information
        """
        return {
            'vault_path': str(self.vault_path),
            'dry_run': self.dry_run,
            'watchers': {
                'gmail': 'running' if 'gmail' in self.processes else 'stopped',
                'filesystem': 'running' if 'filesystem' in self.processes else 'stopped'
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
        """
        Print current system status to console.
        """
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
                'watcher': '[W]',
                'clipboard': '[DOC]'
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
                'watcher': '👁️',
                'clipboard': '📋'
            }

        print("\n" + "=" * 60)
        print(f"{icons['robot']} Digital FTE Status")
        print("=" * 60)
        print(f"\n{icons['vault']} Vault: {status['vault_path']}")
        print(f"{icons['mode']} Mode: {'Dry Run' if status['dry_run'] else 'Production'}")
        print(f"{icons['time']} Updated: {status['timestamp']}")

        print(f"\n{icons['chart']} Folder Status:")
        for folder, count in status['folders'].items():
            icon = icons['red'] if count > 5 else icons['yellow'] if count > 0 else icons['green']
            print(f"  {icon} /{folder}: {count} files")

        print(f"\n{icons['watcher']} Watchers:")
        for watcher, state in status['watchers'].items():
            icon = icons['green'] if state == 'running' else icons['watcher']
            print(f"  {icon} {watcher}: {state}")

        print(f"\n{icons['clipboard']} Dashboard:", status['dashboard'])
        print("=" * 60 + "\n")


def main():
    """Main entry point for orchestrator."""
    import tempfile
    import logging
    
    parser = argparse.ArgumentParser(description='Digital FTE Orchestrator')
    parser.add_argument(
        'command',
        nargs='?',
        choices=['start', 'stop', 'process', 'ralph-loop', 'status'],
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
        default=['gmail', 'filesystem'],
        help='Watchers to start'
    )
    parser.add_argument(
        '--prompt',
        type=str,
        help='Custom prompt for Claude processing'
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
        default=os.getenv('DRY_RUN', 'true').lower() == 'true',
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
        print("🚀 Starting Digital FTE watchers...\n")
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
        print("🛑 Stopping Digital FTE watchers...\n")
        orchestrator.stop_all_watchers()
        orchestrator.print_status()
    
    elif args.command == 'process':
        print("🧠 Triggering Claude Code processing...\n")
        success = orchestrator.trigger_claude_processing(args.prompt)
        if success:
            print("✅ Processing started")
        else:
            print("❌ Processing failed")
            sys.exit(1)
    
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
