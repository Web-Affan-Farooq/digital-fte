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

import base64
import os
import sys
from datetime import datetime
from email import message_from_bytes
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from base_watcher import BaseWatcher

# Gmail API imports (optional, graceful fallback)
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("Gmail API libraries not installed. Install with:")
    print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")


class GmailWatcher(BaseWatcher):
    """
    Watches Gmail for new unread messages and creates action files.
    
    Attributes:
        credentials_path: Path to Gmail credentials.json
        token_path: Path to OAuth token.json
        processed_ids: Set of already processed message IDs
    """

    # Scopes required for Gmail API
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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
        """Load previously processed message IDs from disk."""
        cache_file = self.logs / 'gmail_processed_ids.txt'
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.processed_ids = set(line.strip() for line in f if line.strip())
                self.logger.info(f"Loaded {len(self.processed_ids)} previously processed message IDs")
            except Exception as e:
                self.logger.warning(f"Could not load processed IDs: {e}")
                self.processed_ids = set()
        else:
            self.processed_ids = set()

    def _save_processed_ids(self) -> None:
        """Save processed message IDs to disk."""
        cache_file = self.logs / 'gmail_processed_ids.txt'
        try:
            with open(cache_file, 'w') as f:
                for msg_id in self.processed_ids:
                    f.write(f"{msg_id}\n")
            self.logger.debug(f"Saved {len(self.processed_ids)} processed message IDs")
        except Exception as e:
            self.logger.error(f"Could not save processed IDs: {e}")

    def _authenticate(self) -> bool:
        """
        Authenticate with Gmail API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    self.token_path, self.SCOPES
                )
            except Exception as e:
                self.logger.warning(f"Could not load token: {e}")
                creds = None
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    self.logger.warning("Token refresh failed, re-authenticating")
                    creds = None
            
            if not creds:
                if not self.credentials_path.exists():
                    self.logger.error(
                        f"Credentials file not found: {self.credentials_path}\n"
                        f"Please download credentials.json from Google Cloud Console and place it there."
                    )
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    
                    # Save token
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                    
                    self.logger.info("Authentication successful")
                except Exception as e:
                    self.logger.error(f"Authentication failed: {e}")
                    return False
        
        # Build service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception as e:
            self.logger.error(f"Could not build Gmail service: {e}")
            return False

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check Gmail for new unread messages.
        
        Returns:
            List of message dictionaries with id, snippet, headers
        """
        if not self.service:
            if not self._authenticate():
                return []
        
        try:
            # Build query for unread, important messages
            query = 'is:unread'
            if 'IMPORTANT' in self.label_ids:
                query += ' is:important'
            
            # Fetch messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10  # Limit to 10 at a time
            ).execute()
            
            messages = results.get('messages', [])
            
            # Filter out already processed
            new_messages = []
            for msg in messages:
                msg_id = msg['id']
                if msg_id not in self.processed_ids:
                    # Fetch full message
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='metadata',
                        metadataHeaders=['From', 'To', 'Subject', 'Date']
                    ).execute()
                    
                    new_messages.append({
                        'id': msg_id,
                        'snippet': full_msg.get('snippet', ''),
                        'headers': {
                            h['name']: h['value']
                            for h in full_msg['payload']['headers']
                        }
                    })
            
            return new_messages
            
        except Exception as e:
            self.logger.error(f"Error checking Gmail: {e}")
            return []

    def create_action_file(self, item: Dict[str, Any]) -> Optional[Path]:
        """
        Create a markdown action file for a Gmail message.
        
        Args:
            item: Message dictionary with id, snippet, headers
            
        Returns:
            Path to created file, or None if failed
        """
        try:
            headers = item['headers']
            from_addr = headers.get('From', 'Unknown')
            subject = headers.get('Subject', 'No Subject')
            date = headers.get('Date', datetime.now().isoformat())
            to_addr = headers.get('To', '')
            
            # Determine priority
            priority = self.get_priority(f"{subject} {item['snippet']}")
            
            # Sanitize filename
            safe_subject = self.sanitize_filename(subject[:50])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"EMAIL_{safe_subject}_{timestamp}.md"
            
            # Create content
            content = f"""---
type: email
from: {from_addr}
to: {to_addr}
subject: {subject}
received: {datetime.now().isoformat()}
original_date: {date}
priority: {priority}
status: pending
message_id: {item['id']}
---

# Email: {subject}

## Sender
**From:** {from_addr}

## Received
{date}

## Priority
{priority.upper()}

---

## Content

{item['snippet']}

---

## Suggested Actions

- [ ] Read full email and understand request
- [ ] Draft reply (requires approval before sending)
- [ ] Forward to relevant party (if needed)
- [ ] Archive after processing

## Notes

_Add your notes here_

---

## Processing Log

- **Detected:** {datetime.now().isoformat()}
- **Priority:** {priority}
- **Status:** Pending review

"""
            
            # Write file
            filepath = self.needs_action / filename
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would create: {filepath}")
                self.log_action('email_detected', {
                    'from': from_addr,
                    'subject': subject,
                    'priority': priority
                })
            else:
                filepath.write_text(content, encoding='utf-8')
                self.processed_ids.add(item['id'])
                self._save_processed_ids()
                
                self.logger.info(f"Created action file: {filepath}")
                self.log_action('email_action_created', {
                    'from': from_addr,
                    'subject': subject,
                    'priority': priority,
                    'filepath': str(filepath)
                })
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error creating action file: {e}")
            return None

    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a Gmail message as read.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            if not self._authenticate():
                return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            self.logger.debug(f"Marked message {message_id} as read")
            return True
        except Exception as e:
            self.logger.error(f"Could not mark message as read: {e}")
            return False


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
    print(f"Dry run: {os.getenv('DRY_RUN', 'true')}")
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
