"""
WhatsApp Watcher for Digital FTE

Monitors WhatsApp Web for new messages using Playwright.
Creates action files in the Obsidian vault for messages matching keywords.

Usage:
    uv run python scripts/WhatsappWatcher/main.py
    
Environment Variables:
    WHATSAPP_SESSION_PATH: Path to persist browser session (default: ~/.digital_fte/sessions/whatsapp)
    VAULT_PATH: Path to Obsidian vault (default: ./vault)
    CHECK_INTERVAL: Seconds between checks (default: 30)
    DRY_RUN: Set to 'false' for actual processing
    WHATSAPP_KEYWORDS: Comma-separated keywords to monitor (default: urgent,asap,invoice,payment,help)

Note: Be aware of WhatsApp's terms of service when using automation.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from .helpers import (
    CloseBrowser,
    LoadProcessedMessages,
    CheckForUpdates,
    SaveProcessedMessages,
    # InitializeBrowser,
    CreateActionFile,
    RunWatcher,
    IsBrowserAlive,
    CheckIfLoggedIn,
    ExtractMessageData,
)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Check for testing and production mode 
dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'

from BaseWatcher.base_watcher import BaseWatcher

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not installed. Install with: uv add playwright")


class WhatsAppWatcher(BaseWatcher):
    """
    Watches WhatsApp Web for new messages containing specific keywords.
    
    Attributes:
        session_path: Path to browser session storage
        keywords: List of keywords to monitor
        browser_context: Persistent browser context
    """

    DEFAULT_KEYWORDS = ['urgent', 'asap', 'invoice', 'payment', 'help', 'important']

    def __init__(
        self,
        vault_path: str,
        session_path: Optional[str] = None,
        check_interval: int = 30,
        keywords: Optional[List[str]] = None
    ):
        """
        Initialize the WhatsApp watcher.

        Args:
            vault_path: Path to the Obsidian vault
            session_path: Path to browser session storage
            check_interval: Seconds between checks
            keywords: Keywords to monitor in messages
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright not installed. Install with: uv add playwright"
            )

        super().__init__(vault_path, check_interval)

        # Session path
        if session_path:
            self.session_path = Path(session_path)
        else:
            home = Path.home()
            self.session_path = home / '.digital_fte' / 'sessions' / 'whatsapp'
        
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Keywords to monitor
        env_keywords = os.getenv('WHATSAPP_KEYWORDS')
        if env_keywords:
            self.keywords = [k.strip().lower() for k in env_keywords.split(',')]
        elif keywords:
            self.keywords = [k.lower() for k in keywords]
        else:
            self.keywords = self.DEFAULT_KEYWORDS

        self.logger.info(f"Monitoring keywords: {self.keywords}")

        # Browser state
        self.playwright = None
        self.browser_context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Track processed messages
        self.processed_messages: set = set()
        self._load_processed_messages()

    def _close_browser(self) -> None:
        return CloseBrowser(self)

# Don't attach underscore because it's abstract method 
    def check_for_updates(self) -> List[Dict[str, Any]]:
        return CheckForUpdates(self)

    def _load_processed_messages(self) -> None:
        return LoadProcessedMessages(self)

    def _save_processed_messages(self) -> None:
       return SaveProcessedMessages(self)

    # def _init_browser(self) -> bool:
    #     return InitializeBrowser(self)

    def _is_browser_alive(self) -> bool:
        """Check if browser is still responsive."""
        return IsBrowserAlive(self)

    def _check_if_logged_in(self) -> bool:
        """Check if WhatsApp Web is logged in."""
        return CheckIfLoggedIn(self)

    def _extract_message_data(self, chat_element) -> Dict[str, Any]:
        """Extract message data from a chat element."""
        return ExtractMessageData(self, chat_element)

    def create_action_file(self, item: Dict[str, Any]) -> Optional[Path]:
        return CreateActionFile(self, item)

    def run(self) -> None:
        return RunWatcher(self)


def main():
    """Main entry point for WhatsApp watcher."""
    import argparse
    
    parser = argparse.ArgumentParser(description='WhatsApp Watcher for Digital FTE')
    parser.add_argument(
        '--vault',
        type=str,
        default=os.getenv('VAULT_PATH', './vault'),
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--session-path',
        type=str,
        default=os.getenv('WHATSAPP_SESSION_PATH'),
        help='Path to browser session storage'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=int(os.getenv('CHECK_INTERVAL', '30')),
        help='Check interval in seconds'
    )
    parser.add_argument(
        '--keywords',
        type=str,
        default=None,
        help='Comma-separated keywords to monitor'
    )
    
    args = parser.parse_args()
    
    if not PLAYWRIGHT_AVAILABLE:
        print("\n❌ Playwright not installed.")
        print("\nInstall with:")
        print("  uv add playwright")
        print("  uv run playwright install chromium\n")
        sys.exit(1)
    
    print("💬 WhatsApp Watcher")
    print("=" * 50)
    print(f"Vault: {args.vault}")
    print(f"Session path: {args.session_path or '~/.digital_fte/sessions/whatsapp'}")
    print(f"Check interval: {args.interval}s")
    print(f"Dry run: {dry_run}")
    print("\nStarting watcher... (Press Ctrl+C to stop)")
    print("Note: First run requires QR code scan to login to WhatsApp Web\n")
    
    keywords = args.keywords.split(',') if args.keywords else None
    
    try:
        watcher = WhatsAppWatcher(
            vault_path=args.vault,
            session_path=args.session_path,
            check_interval=args.interval,
            keywords=keywords
        )
        watcher.run()
    except KeyboardInterrupt:
        print("\n\n👋 Watcher stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
