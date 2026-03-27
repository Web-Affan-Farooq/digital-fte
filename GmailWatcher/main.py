"""
Gmail Watcher for Digital FTE

This script monitors Gmail for new unread messages and creates
actionable markdown files in the Obsidian vault.

Setup Requirements:
1. Enable Gmail API: https://developers.google.com/gmail/api/quickstart/python
2. Download credentials.json from Google Cloud Console
3. Run once to authorize: python gmail_watcher.py --auth
4. Set environment variables in .env file

Usage:
    python scripts/gmail_watcher.py
    
Environment Variables:
    GMAIL_CREDENTIALS_PATH: Path to credentials.json (default: ~/.gmail/credentials.json)
    GMAIL_TOKEN_PATH: Path to token.json (default: ~/.gmail/token.json)
    VAULT_PATH: Path to Obsidian vault (default: ./vault)
    DRY_RUN: Set to 'false' to enable actual processing
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from BaseWatcher import BaseWatcher

# Gmail API imports (optional, graceful fallback)
try:
    import google.oauth2.credentials
    import google_auth_oauthlib.flow
    import googleapiclient.discovery
    import google.auth.transport.requests
    import google.auth.exceptions  
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("Gmail API libraries not installed. Install with:")
    print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

## Helper utililties :
from .helpers import (
    Authenticate , LoadProcessedIds , CreateActionFiles , MarkAsRead , SaveProcessedIds , CheckForUpdates
)
class GmailWatcher(BaseWatcher):
    """
    Watches Gmail for new unread messages and creates action files.
    
    Attributes:
        credentials_path: Path to Gmail credentials.json
        token_path: Path to OAuth token.json
        processed_ids: Set of already processed message IDs
    """

    # Scopes required for Gmail API
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.compose' , "https://www.googleapis.com/auth/gmail.modify"]

    def __init__(
        self,
        vault_path: str,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        check_interval: int = 120,
        label_ids: Optional[List[str]] = None
    ):
        """
        Initialize the Gmail watcher.

        Args:
            vault_path: Path to the Obsidian vault
            credentials_path: Path to Gmail credentials.json
            token_path: Path to OAuth token.json
            check_interval: Seconds between checks (default: 120)
            label_ids: Gmail label IDs to filter (default: ['UNREAD', 'IMPORTANT'])
        """
        if not GMAIL_AVAILABLE:
            raise ImportError(
                "Gmail API libraries not installed. "
                "Install with: pip install google-api-python-client "
                "google-auth-httplib2 google-auth-oauthlib"
            )

        super().__init__(vault_path, check_interval)

        # Default paths
        home = Path.home()
        gmail_dir = home / '.gmail_watcher'
        gmail_dir.mkdir(parents=True, exist_ok=True)

        self.credentials_path = Path(credentials_path) if credentials_path else gmail_dir / 'credentials.json'
        self.token_path = Path(token_path) if token_path else gmail_dir / 'token.json'
        
        # Default to UNREAD and IMPORTANT labels
        self.label_ids = label_ids or ['UNREAD', 'IMPORTANT']
        
        # Gmail service (initialized on first use)
        self.service = None
        
        # Load previously processed message IDs
        self._load_processed_ids()

    def _load_processed_ids(self) -> None:
        return LoadProcessedIds(self)

    def _authenticate(self) -> bool:
        return Authenticate(self)

    def create_action_file(self, item: Dict[str, Any]) -> Optional[Path]:
        return CreateActionFiles(self , item)

    def mark_as_read(self, message_id: str) -> bool:
       return MarkAsRead(self , message_id)
    
    def _save_processed_ids(self) -> None:
       return SaveProcessedIds(self)

    def check_for_updates(self) -> List[Dict[str, Any]]:
        return CheckForUpdates(self)       

def main():
    """Main entry point for Gmail watcher."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gmail Watcher for Digital FTE')
    parser.add_argument(
        '--auth',
        action='store_true',
        help='Run authentication flow only'
    )
    parser.add_argument(
        '--vault',
        type=str,
        default=os.getenv('VAULT_PATH', './vault'),
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--credentials',
        type=str,
        default=os.getenv('GMAIL_CREDENTIALS_PATH'),
        help='Path to Gmail credentials.json'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=120,
        help='Check interval in seconds'
    )
    
    args = parser.parse_args()
    
    # Check if Gmail libraries are available
    if not GMAIL_AVAILABLE:
        print("\n❌ Gmail API libraries not installed.")
        print("\nInstall with:")
        print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        print("\nThen set up your credentials:")
        print("  1. Go to https://developers.google.com/gmail/api/quickstart/python")
        print("  2. Download credentials.json")
        print("  3. Place in ~/.gmail_watcher/credentials.json")
        print("  4. Run: python gmail_watcher.py --auth\n")
        sys.exit(1)
    
    # Authentication only mode
    if args.auth:
        print("🔐 Gmail Authentication")
        print("=" * 50)
        watcher = GmailWatcher(
            vault_path=args.vault,
            credentials_path=args.credentials
        )
        if watcher._authenticate():
            print("\n✅ Authentication successful!")
            print(f"Token saved to: {watcher.token_path}")
            sys.exit(0)
        else:
            print("\n❌ Authentication failed!")
            sys.exit(1)
    
    # Normal watcher mode
    print("📧 Gmail Watcher")
    print("=" * 50)
    print(f"Vault: {args.vault}")
    print(f"Check interval: {args.interval}s")
    print(f"Dry run: {dry_run}")
    print("\nStarting watcher... (Press Ctrl+C to stop)\n")
    
    try:
        watcher = GmailWatcher(
            vault_path=args.vault,
            credentials_path=args.credentials,
            check_interval=args.interval
        )
        watcher.run()
    except KeyboardInterrupt:
        print("\n\n👋 Watcher stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
