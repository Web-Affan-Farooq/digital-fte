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
    uv run python scripts/Orchesterator/main.py start

    # Start MCP servers
    uv run python scripts/Orchesterator/main.py start-mcp

    # Process Needs_Action folder with qwen
    uv run python scripts/Orchesterator/main.py process

    # Process approved actions
    uv run python scripts/Orchesterator/main.py process-approvals

    # Start Ralph Wiggum loop
    uv run python scripts/Orchesterator/main.py ralph-loop "Process all files"

    # Check system status
    uv run python scripts/Orchesterator/main.py status

Environment Variables:
    VAULT_PATH: Path to Obsidian vault (default: ./vault)
    DRY_RUN: Set to 'false' to enable actual processing
    MAX_ITERATIONS: Max Ralph loop iterations (default: 10)
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich import print

from .helpers import (
    EnsureDirectories,
    SetupLogging,
    CountFiles,
    FindQwenExecutable,
    UpdateDashboard,
    StartWatcher,
    StopWatcher,
    StartMcpServer,
    StopMcpServer,
    GetApprovedActions,
    ProcessApprovedAction,
    ExecuteEmailAction,
    ExecuteLinkedinAction,
    GetNeedsActionFiles,
    TriggerQwenProcessing,
    RalphLoop,
    GetStatus,
    PrintStatus,
)

# Global dry run flag
dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'


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
        return EnsureDirectories(self)

    def _setup_logging(self) -> Any:
        return SetupLogging(self)

    def _count_files(self, folder: Path) -> int:
        return CountFiles(self, folder)

    def _find_qwen_executable(self) -> Optional[str]:
        return FindQwenExecutable(self)

    def update_dashboard(self) -> None:
        return UpdateDashboard(self)

    def start_watcher(self, watcher_name: str) -> bool:
        return StartWatcher(self, watcher_name)

    def stop_watcher(self, watcher_name: str) -> bool:
        return StopWatcher(self, watcher_name)

    def start_mcp_server(self, server_name: str) -> bool:
        return StartMcpServer(self, server_name)

    def stop_mcp_server(self, server_name: str) -> bool:
        return StopMcpServer(self, server_name)

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
        return GetApprovedActions(self)

    def process_approved_action(self, filepath: Path) -> bool:
        return ProcessApprovedAction(self, filepath)

    def _execute_email_action(self, filepath: Path, metadata: Dict, content: str) -> bool:
        return ExecuteEmailAction(self, filepath, metadata, content)

    def _execute_linkedin_action(self, filepath: Path, metadata: Dict, content: str) -> bool:
        return ExecuteLinkedinAction(self, filepath, metadata, content)

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
        return GetNeedsActionFiles(self)

    def trigger_qwen_processing(self, prompt: Optional[str] = None) -> bool:
        return TriggerQwenProcessing(self, prompt)

    def ralph_loop(self, prompt: str, completion_promise: str = "TASK_COMPLETE") -> None:
        return RalphLoop(self, prompt, completion_promise)

    def get_status(self) -> Dict[str, Any]:
        return GetStatus(self)

    def print_status(self) -> None:
        return PrintStatus(self)


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
        help='Custom prompt for qwen processing'
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
        print("🧠 Triggering qwen code processing...\n")
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
