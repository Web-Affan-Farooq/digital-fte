from typing import List, Dict, Any
import time
import datetime

def CheckForUpdates(self) -> List[Dict[str, Any]]:
    """
    Check WhatsApp Web for new messages containing keywords.

    This method does NOT reload the page - it relies on WhatsApp's real-time updates.
    WhatsApp Web automatically pushes new messages, so we just need to check the DOM.

    Returns:
        List of message dictionaries
    """
    # Ensure browser is initialized (but don't reload if already running)
    if not self.browser_context:
        self.logger.info("Browser not initialized, initializing now...")
        if not self._init_browser():
            return []

    # Verify browser is still alive
    if not self._is_browser_alive():
        self.logger.warning("Browser died, reinitializing...")
        self._close_browser()
        time.sleep(2)
        if not self._init_browser():
            return []

    try:
        # Small wait to ensure page is stable
        time.sleep(2)

        messages = []

        # Scroll the chat list to ensure all chats are loaded
        try:
            chat_list_panel = self.page.query_selector('[data-testid="chat-list"]')
            if chat_list_panel:
                # Scroll down and up to load all chats
                chat_list_panel.evaluate('el => { el.scrollTop = el.scrollHeight; }')
                time.sleep(0.5)
                chat_list_panel.evaluate('el => { el.scrollTop = 0; }')
                time.sleep(0.5)
                self.logger.debug("Scrolled chat list to load all chats")
        except Exception as e:
            self.logger.debug(f"Could not scroll chat list: {e}")

        # Get all chat items from the chat list
        try:
            # WhatsApp Web structure: chats are in a list with role="listitem"
            # Each chat has a specific structure we can target
            chat_items = self.page.query_selector_all('[role="listitem"]')

            self.logger.info(f"Found {len(chat_items)} chat items in chat list")

            for idx, chat in enumerate(chat_items[:50]):  # Limit to first 50 chats
                try:
                    message_data = self._extract_message_data(chat)

                    if message_data:
                        self.logger.debug(
                            f"Chat {idx}: '{message_data['chat_name']}' - " +
                            f"Unread: {message_data['has_unread']}, " +
                            f"Message: {message_data['message_text'][:50] if message_data['message_text'] else 'N/A'}..."
                        )

                        # Check for unread messages
                        if message_data['has_unread']:
                            self.logger.info(
                                f"🔔 Unread message detected from '{message_data['chat_name']}'"
                            )

                            # Check for keywords in the message
                            message_lower = message_data['message_text'].lower()
                            matched_keywords = [kw for kw in self.keywords if kw in message_lower]

                            if matched_keywords:
                                # Create unique message ID
                                msg_id = f"{message_data['chat_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                                if msg_id not in self.processed_messages:
                                    message_data['id'] = msg_id
                                    message_data['matched_keywords'] = matched_keywords
                                    message_data['timestamp'] = datetime.now().isoformat()
                                    messages.append(message_data)

                                    self.logger.info(
                                        f"📩 MATCHING message from '{message_data['chat_name']}' " +
                                        f"(keywords: {', '.join(matched_keywords)})"
                                    )
                            else:
                                self.logger.debug(
                                    f"  Unread but no keyword match. Keywords monitored: {self.keywords}"
                                )

                except Exception as e:
                    self.logger.debug(f"Error processing chat {idx}: {e}")
                    continue

        except Exception as e:
            self.logger.debug(f"Error finding chat list: {e}")

        # Log summary
        if messages:
            self.logger.info(f"✅ Found {len(messages)} new matching message(s)")
        else:
            self.logger.info("No new matching messages found in this cycle")

        return messages

    except Exception as e:
        self.logger.error(f"Error checking WhatsApp messages: {e}")
        # Don't close browser on error - just return empty and try again next cycle
        return []


def ExtractMessageData(self, chat_element) -> Dict[str, Any]:
    """
    Extract message data from a chat list item element.

    Args:
        chat_element: Playwright element handle for a chat item

    Returns:
        Dictionary with chat_name, message_text, has_unread, etc.
    """
    result = {
        'chat_name': 'Unknown',
        'message_text': '',
        'has_unread': False,
        'timestamp': None
    }

    try:
        # Extract chat name - usually in a span with title attribute
        try:
            chat_name_el = chat_element.query_selector('span[title]')
            if chat_name_el:
                result['chat_name'] = chat_name_el.get_attribute('title') or 'Unknown'
            
            # Fallback: try aria-label
            if result['chat_name'] == 'Unknown':
                aria_label = chat_element.get_attribute('aria-label')
                if aria_label:
                    result['chat_name'] = aria_label.split(',')[0] or 'Unknown'
        except Exception as e:
            self.logger.debug(f"Error extracting chat name: {e}")

        # Check for unread indicator
        # WhatsApp uses multiple indicators for unread messages
        try:
            # Primary unread selectors - green badge with number
            unread_selectors = [
                '[aria-label*="unread "]',           # Aria label with "unread"
                'span[aria-label*="unread"]',       # Span with unread aria
                '[data-testid="unread-marker"]',    # Unread marker testid
                'span[class*="unread"]',            # Class containing "unread"
                'div[class*="unread"]',             # Div with unread class
                'span[class*="_ac3b"]',             # WhatsApp's unread badge class
                'span[class*="iuthp"]',             # Alternative unread class
                'span[aria-label]',                 # Any aria-label (often contains "unread, X messages")
            ]

            for selector in unread_selectors:
                try:
                    unread_el = chat_element.query_selector(selector)
                    if unread_el:
                        # Double-check: get aria-label to confirm it's actually unread
                        aria_label = chat_element.get_attribute('aria-label')
                        if aria_label and 'unread' in aria_label.lower():
                            result['has_unread'] = True
                            self.logger.debug(f"Unread detected via {selector}, aria-label: {aria_label}")
                            break
                        # Also check for green dot/badge visually
                        unread_text = unread_el.inner_text().strip()
                        if unread_text and unread_text.isdigit():
                            result['has_unread'] = True
                            self.logger.debug(f"Unread detected via {selector}, count: {unread_text}")
                            break
                        # If element exists and looks like unread marker
                        unread_class = unread_el.get_attribute('class') or ''
                        if 'unread' in unread_class.lower() or '_ac3b' in unread_class or 'iuthp' in unread_class:
                            result['has_unread'] = True
                            self.logger.debug(f"Unread detected via {selector}, class: {unread_class}")
                            break
                except Exception:
                    continue

            # Fallback: check aria-label directly on chat element
            if not result['has_unread']:
                try:
                    aria_label = chat_element.get_attribute('aria-label')
                    if aria_label and 'unread' in aria_label.lower():
                        result['has_unread'] = True
                        self.logger.debug(f"Unread detected via chat aria-label: {aria_label}")
                except Exception:
                    pass

        except Exception as e:
            self.logger.debug(f"Error checking unread status: {e}")

        # Extract last message text
        # WhatsApp structure: message text is typically in spans with specific testids
        try:
            # Primary selectors for message preview
            message_selectors = [
                'span[data-testid="message-preview"]',      # Last message preview
                'span[data-testid="last-message"]',         # Last message
                'div[data-testid="chat-list-message"]',     # Chat list message
                'span[dir="auto"]',                         # Auto-direction text (common for messages)
            ]

            for selector in message_selectors:
                try:
                    msg_el = chat_element.query_selector(selector)
                    if msg_el:
                        text = msg_el.inner_text().strip()
                        if text and len(text) > 1:
                            result['message_text'] = text
                            self.logger.debug(f"Message found via {selector}: {text[:50]}...")
                            break
                except Exception:
                    continue

            # Fallback: Get all spans and look for message content
            if not result['message_text']:
                all_spans = chat_element.query_selector_all('span')

                # Check last few spans (message text is usually near the end)
                for span in reversed(all_spans[-8:]):
                    try:
                        text = span.inner_text().strip()
                        # Skip empty, very short, timestamps, or meta text
                        if text and len(text) > 2 and not text.startswith('http') and not text.replace(':', '').replace('-', '').replace('/', '').isdigit():
                            # Skip if it looks like a time (e.g., "10:30 AM")
                            if not any(c.isdigit() for c in text[:2]) or len(text) > 10:
                                result['message_text'] = text
                                self.logger.debug(f"Message found in span: {text[:50]}...")
                                break
                    except Exception:
                        continue

            # Last resort: get all text content
            if not result['message_text']:
                try:
                    all_text = chat_element.inner_text().strip()
                    # Try to extract just the message part
                    lines = all_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 3 and not line[0].isdigit():
                            result['message_text'] = line[:200]
                            break
                except Exception:
                    pass

        except Exception as e:
            self.logger.debug(f"Error extracting message text: {e}")

        return result

    except Exception as e:
        self.logger.debug(f"Error extracting message data: {e}")
        return result


def IsBrowserAlive(self) -> bool:
    """
    Check if the browser context and page are still alive.
    
    Returns:
        True if browser is responsive, False otherwise
    """
    try:
        if not self.browser_context:
            return False
        
        if not self.page:
            return False
        
        # Try to get page title - will raise exception if page is closed
        self.page.title()
        
        # Check if page is not closed
        if self.page.is_closed():
            return False
        
        return True
        
    except Exception as e:
        self.logger.debug(f"Browser health check failed: {e}")
        return False
