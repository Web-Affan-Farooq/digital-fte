"""
WhatsApp Watcher for Digital FTE

Monitors WhatsApp Web for new messages using Playwright.
Creates action files in the Obsidian vault for messages matching keywords.

Usage:
    uv run python scripts/whatsapp_watcher.py
    
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
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from config.settings import dry_run

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from base_watcher import BaseWatcher

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

    def _load_processed_messages(self) -> None:
        """Load previously processed message IDs from disk."""
        cache_file = self.logs / 'whatsapp_processed_messages.json'
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self.processed_messages = set(data.get('ids', []))
                self.logger.info(f"Loaded {len(self.processed_messages)} previously processed messages")
            except Exception as e:
                self.logger.warning(f"Could not load processed messages: {e}")
                self.processed_messages = set()
        else:
            self.processed_messages = set()

    def _save_processed_messages(self) -> None:
        """Save processed message IDs to disk."""
        cache_file = self.logs / 'whatsapp_processed_messages.json'
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'ids': list(self.processed_messages),
                    'updated': datetime.now().isoformat()
                }, f)
            self.logger.debug(f"Saved {len(self.processed_messages)} processed message IDs")
        except Exception as e:
            self.logger.error(f"Could not save processed messages: {e}")

    def _init_browser(self) -> bool:
        """
        Initialize the browser and navigate to WhatsApp Web.
        
        Returns:
            True if successful
        """
        try:
            from playwright.sync_api import sync_playwright
            
            self.playwright = sync_playwright().start()
            
            # Launch persistent browser context
            self.browser_context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_path),
                headless=os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            self.page = self.browser_context.pages[0] if self.browser_context.pages else self.browser_context.new_page()
            
            # Navigate to WhatsApp Web
            self.page.goto('https://web.whatsapp.com')
            
            self.logger.info("WhatsApp Web loaded. Scan QR code if not already logged in.")
            
            # Wait for chat list (indicates login)
            try:
                self.page.wait_for_selector('[data-testid="chat-list"]', timeout=60000)
                self.logger.info("WhatsApp Web logged in successfully")
                return True
            except Exception:
                self.logger.warning("QR code may need to be scanned. Waiting...")
                return True  # Continue anyway, user can scan
                
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {e}")
            return False

    def _close_browser(self) -> None:
        """Close the browser."""
        if self.browser_context:
            try:
                self.browser_context.close()
            except Exception:
                pass
            self.browser_context = None
        
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
        
        self.page = None

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check WhatsApp Web for new messages containing keywords.
        
        Returns:
            List of message dictionaries
        """
        if not self.browser_context:
            if not self._init_browser():
                return []
        
        try:
            # Refresh page to get latest messages
            self.page.reload()
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)  # Wait for messages to load
            
            # Find unread chats
            messages = []
            
            # Try to find unread message indicators
            try:
                # Look for elements with unread indicators
                unread_chats = self.page.query_selector_all('[aria-label*="unread"], [data-testid="unread-marker"]')
                
                for chat in unread_chats:
                    try:
                        # Get chat name
                        chat_name_el = chat.locator('span[title]').first
                        chat_name = chat_name_el.get_attribute('title') if chat_name_el else 'Unknown'
                        
                        # Get last message text
                        message_el = chat.locator('span[title]:not([aria-label])').last
                        message_text = message_el.inner_text() if message_el else ''
                        
                        # Check for keywords
                        message_lower = message_text.lower()
                        matched_keywords = [kw for kw in self.keywords if kw in message_lower]
                        
                        if matched_keywords:
                            # Create unique message ID
                            msg_id = f"{chat_name}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                            
                            if msg_id not in self.processed_messages:
                                messages.append({
                                    'id': msg_id,
                                    'chat_name': chat_name,
                                    'message_text': message_text,
                                    'matched_keywords': matched_keywords,
                                    'timestamp': datetime.now().isoformat()
                                })
                    except Exception as e:
                        self.logger.debug(f"Error processing chat: {e}")
                        continue
                        
            except Exception as e:
                self.logger.debug(f"Error finding unread chats: {e}")
            
            # Alternative: Check all visible chats for keywords
            if not messages:
                try:
                    all_chats = self.page.query_selector_all('[role="listitem"]')
                    
                    for chat in all_chats[:20]:  # Limit to first 20 chats
                        try:
                            chat_name_el = chat.locator('span[title]').first
                            chat_name = chat_name_el.get_attribute('title') if chat_name_el else 'Unknown'
                            
                            message_el = chat.locator('span[title]:not([aria-label])').last
                            message_text = message_el.inner_text() if message_el else ''
                            
                            message_lower = message_text.lower()
                            matched_keywords = [kw for kw in self.keywords if kw in message_lower]
                            
                            if matched_keywords:
                                msg_id = f"{chat_name}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                                
                                if msg_id not in self.processed_messages:
                                    messages.append({
                                        'id': msg_id,
                                        'chat_name': chat_name,
                                        'message_text': message_text,
                                        'matched_keywords': matched_keywords,
                                        'timestamp': datetime.now().isoformat(),
                                        'is_unread': False
                                    })
                        except Exception:
                            continue
                except Exception as e:
                    self.logger.debug(f"Error checking all chats: {e}")
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error checking WhatsApp: {e}")
            # Try to recover by reinitializing
            self._close_browser()
            return []

    def create_action_file(self, item: Dict[str, Any]) -> Optional[Path]:
        """
        Create a markdown action file for a WhatsApp message.
        
        Args:
            item: Message dictionary
            
        Returns:
            Path to created file, or None if failed
        """
        try:
            chat_name = self.sanitize_filename(item.get('chat_name', 'Unknown'))
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"WHATSAPP_{chat_name}_{timestamp}.md"
            
            priority = 'high' if 'urgent' in item['matched_keywords'] or 'asap' in item['matched_keywords'] else 'normal'
            
            content = f"""---
type: whatsapp_message
chat_name: {item['chat_name']}
received: {item['timestamp']}
priority: {priority}
status: pending
matched_keywords: {item['matched_keywords']}
message_id: {item['id']}
---

# WhatsApp Message

## From
**{item['chat_name']}**

## Received
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Priority
{priority.upper()}

## Matched Keywords
{', '.join(item['matched_keywords'])}

---

## Message Content

{item['message_text']}

---

## Suggested Actions

- [ ] Read and understand the message
- [ ] Draft reply (requires approval before sending)
- [ ] Take necessary action based on request
- [ ] Mark as processed

## Reply Draft

_Write your reply here. Move to /Approved when ready to send._

---

## Processing Log

- **Detected:** {datetime.now().isoformat()}
- **Priority:** {priority}
- **Status:** Pending review

"""
            
            filepath = self.needs_action / filename
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would create: {filepath}")
                self.log_action('whatsapp_message_detected', {
                    'from': item['chat_name'],
                    'keywords': item['matched_keywords'],
                    'priority': priority
                })
            else:
                filepath.write_text(content, encoding='utf-8')
                self.processed_messages.add(item['id'])
                self._save_processed_messages()
                
                self.logger.info(f"Created action file: {filepath}")
                self.log_action('whatsapp_action_created', {
                    'from': item['chat_name'],
                    'keywords': item['matched_keywords'],
                    'priority': priority,
                    'filepath': str(filepath)
                })
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error creating action file: {e}")
            return None

    def run(self) -> None:
        """
        Main run loop for the WhatsApp watcher.
        """
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Vault path: {self.vault_path}")
        self.logger.info(f"Session path: {self.session_path}")
        self.logger.info(f"Check interval: {self.check_interval}s")
        self.logger.info(f"Dry run mode: {self.dry_run}")
        self.logger.info(f"Keywords: {self.keywords}")
        
        try:
            # Initialize browser
            if not self._init_browser():
                self.logger.error("Failed to initialize browser. Exiting.")
                return
            
            while True:
                try:
                    items = self.check_for_updates()
                    
                    if items:
                        self.logger.info(f"Found {len(items)} new message(s)")
                        
                        for item in items:
                            if self.dry_run:
                                self.logger.info(f"[DRY RUN] Would process message from {item['chat_name']}")
                            else:
                                filepath = self.create_action_file(item)
                                if filepath:
                                    self.logger.info(f"Created action file: {filepath}")
                    else:
                        self.logger.debug("No new messages found")
                    
                except Exception as e:
                    self.logger.error(f"Error processing messages: {e}")
                    # Try to recover
                    self._close_browser()
                    time.sleep(5)
                    self._init_browser()
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info(f"{self.__class__.__name__} stopped by user")
        finally:
            self._close_browser()


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
