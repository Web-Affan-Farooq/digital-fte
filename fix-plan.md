# WhatsApp Watcher Fix Plan

## Executive Summary

The WhatsApp Watcher is failing to detect unread messages because WhatsApp Web has updated its DOM structure. The current selectors in `check_for_updates.py` are not matching the actual elements rendered by WhatsApp Web's React-based UI.

This document provides:
1. **Identified Issues** - Root causes of the detection failure
2. **Implementation Plan** - Step-by-step fixes for each issue
3. **Testing Strategy** - How to verify the fixes work correctly

---

## Part 1: Identified Issues

### Issue #1: Outdated/Incorrect Selectors for Chat List

**Current Problem:**
The script uses `[data-testid="chat-list"]` as the primary selector, but WhatsApp Web's current structure may use different attributes.

**Evidence Needed:**
Run `inspect_dom.py` to identify the actual chat list container selector.

**Likely Causes:**
- WhatsApp changed from `data-testid="chat-list"` to `role="list"` or other attributes
- The chat list might be nested inside multiple `div` containers
- Shadow DOM might be involved (less likely but possible)

---

### Issue #2: Unread Message Indicator Detection Failure

**Current Problem:**
The script looks for:
- `[aria-label*="unread"]`
- `[data-testid="unread-marker"]`
- `span[class*="unread"]`
- `span[class*="_ac3b"]`
- `span[class*="iuthp"]`

None of these are reliably detecting unread messages.

**Likely Causes:**
1. **Dynamic Class Names**: WhatsApp uses hashed CSS classes (e.g., `_ac3b`, `Ep61I`, `P1v7c`) that change with updates
2. **SVG Indicators**: Unread might be indicated by SVG icons instead of text badges
3. **Color-Based Detection**: Unread chats might only be distinguished by background color, not explicit markers
4. **Aria Label Changes**: The aria-label format might have changed (e.g., from "unread, 3 messages" to "3 unread messages")

---

### Issue #3: Message Preview Text Extraction

**Current Problem:**
The script cannot extract message text from chat items.

**Current Selectors:**
- `span[data-testid="message-preview"]`
- `span[data-testid="last-message"]`
- `div[data-testid="chat-list-message"]`
- `span[dir="auto"]`

**Likely Causes:**
- Message text might be in nested spans without testid attributes
- WhatsApp might be using `div` instead of `span` for message previews
- The text might be split across multiple elements (sender name + message content)

---

### Issue #4: Chat Name Extraction

**Current Problem:**
Chat names are not being extracted reliably.

**Current Approach:**
- Looking for `span[title]`
- Fallback to `aria-label`

**Likely Causes:**
- Chat names might be in `div` elements instead of `span`
- The `title` attribute might not be present on all chat items
- Group chats vs individual chats might have different structures

---

### Issue #5: Timing and Loading Issues

**Current Problem:**
Elements might not be immediately available when the script checks.

**Current Approach:**
- 2-second sleep after page load
- No explicit waits for specific elements

**Likely Causes:**
- WhatsApp Web uses lazy loading for chat items
- The chat list might render before messages are loaded
- Network requests might delay content availability

---

### Issue #6: Shadow DOM or React Component Boundaries

**Current Problem:**
Playwright's `query_selector` might not penetrate React component boundaries.

**Investigation Needed:**
- Check if chat list uses Shadow DOM
- Verify if React's virtual DOM affects selector behavior

---

## Part 2: Implementation Plan

### Fix #1: Update Chat List Selector

**Steps:**

1. **Run DOM Inspector:**
   ```bash
   cd WhatsappWatcher
   uv run python inspect_dom.py
   ```

2. **Review Output:**
   - Check section "### 2. CHAT LIST PANEL ###"
   - Identify which selector found the chat list
   - Note the `role`, `data-testid`, and `class` attributes

3. **Update `check_for_updates.py`:**
   ```python
   # Replace this section in check_for_updates():
   
   # OLD:
   chat_items = self.page.query_selector_all('[role="listitem"]')
   
   # NEW (example - adjust based on inspection):
   chat_list_selectors = [
       '[data-testid="chat-list"]',
       '[role="list"]',
       '#pane-side',
       '[data-asset-testid="chat-list"]'
   ]
   
   chat_list = None
   for selector in chat_list_selectors:
       chat_list = self.page.query_selector(selector)
       if chat_list:
           self.logger.debug(f"Chat list found via: {selector}")
           break
   
   if not chat_list:
       self.logger.warning("Chat list not found")
       return []
   
   chat_items = chat_list.query_selector_all('[role="listitem"]')
   ```

**Expected Outcome:** Chat list container correctly identified

---

### Fix #2: Update Unread Message Detection

**Steps:**

1. **From DOM Inspector Output:**
   - Check section "### 4. UNREAD INDICATORS ###"
   - Note all selectors that found unread badges
   - Pay attention to:
     - Actual class names (e.g., `Ep61I`, `P1v7c`)
     - Aria-label format
     - Parent element structure

2. **Implement Multi-Strategy Detection:**
   ```python
   def _check_unread_status(self, chat_element) -> bool:
       """Check if a chat has unread messages using multiple strategies."""
       
       # Strategy 1: Aria-label containing "unread"
       aria_label = chat_element.get_attribute('aria-label')
       if aria_label and 'unread' in aria_label.lower():
           self.logger.debug(f"Unread via aria-label: {aria_label}")
           return True
       
       # Strategy 2: Look for unread badge by class patterns
       # WhatsApp typically uses hashed classes like ._ac3b, .Ep61I, .P1v7c
       unread_class_patterns = [
           '_ac3b', 'iuthp', 'Ep61I', 'P1v7c',  # Common patterns
           'unread', 'message', 'badge'  # Fallback keywords
       ]
       
       for pattern in unread_class_patterns:
           try:
               badge = chat_element.query_selector(f'span[class*="{pattern}"]')
               if badge:
                   badge_text = badge.inner_text().strip()
                   # If badge has a number, it's likely an unread count
                   if badge_text and badge_text.isdigit() and int(badge_text) > 0:
                       self.logger.debug(f"Unread badge found: {badge_text}")
                       return True
           except Exception:
               continue
       
       # Strategy 3: Check for green dot indicator (SVG)
       try:
           # WhatsApp uses green circles for unread chats
           green_indicators = chat_element.query_selector_all('svg')
           for svg in green_indicators:
               # Check if SVG has green fill or circle
               svg_html = svg.inner_html()
               if 'fill' in svg_html and ('#25D366' in svg_html or 'green' in svg_html.lower()):
                   self.logger.debug("Green SVG indicator found")
                   return True
       except Exception:
               pass
       
       # Strategy 4: Check parent chat item for "unread" class
       try:
           chat_class = chat_element.get_attribute('class') or ''
           if any(p in chat_class.lower() for p in ['unread', 'active']):
               self.logger.debug(f"Chat has unread-related class: {chat_class}")
               return True
       except Exception:
               pass
       
       return False
   ```

3. **Update `ExtractMessageData()` Function:**
   Replace the unread detection section with the new multi-strategy approach.

**Expected Outcome:** Unread messages detected reliably

---

### Fix #3: Update Message Text Extraction

**Steps:**

1. **From DOM Inspector Output:**
   - Check section "### 5. MESSAGE PREVIEW TEXT ###"
   - Identify which elements contain message text
   - Note the hierarchy: chat item → message container → text element

2. **Implement Robust Text Extraction:**
   ```python
   def _extract_message_text(self, chat_element) -> str:
       """Extract the last message preview text from a chat item."""
       
       # Strategy 1: Look for message preview by testid
       preview_selectors = [
           'span[data-testid="message-preview"]',
           'span[data-testid="last-message"]',
           'div[data-testid="chat-list-message"]',
       ]
       
       for selector in preview_selectors:
           try:
               msg_el = chat_element.query_selector(selector)
               if msg_el:
                   text = msg_el.inner_text().strip()
                   if text and len(text) > 2:
                       self.logger.debug(f"Message found via {selector}: {text[:50]}")
                       return text
           except Exception:
               continue
       
       # Strategy 2: Look for spans with dir="auto" (common for user-generated text)
       try:
           auto_spans = chat_element.query_selector_all('span[dir="auto"]')
           for span in auto_spans:
               text = span.inner_text().strip()
               # Filter out timestamps and sender names
               if text and len(text) > 5 and not self._is_timestamp(text):
                   self.logger.debug(f"Message found in dir=auto span: {text[:50]}")
                   return text
       except Exception:
               pass
       
       # Strategy 3: Get all text and parse intelligently
       try:
           all_text = chat_element.inner_text()
           lines = [line.strip() for line in all_text.split('\n') if line.strip()]
           
           # Typically: [Chat Name] [Message Preview] [Timestamp]
           # We want the message preview (usually second-to-last non-timestamp line)
           for line in reversed(lines):
               if len(line) > 5 and not self._is_timestamp(line) and not self._is_sender_name(line):
                   self.logger.debug(f"Message parsed from full text: {line[:50]}")
                   return line
       except Exception:
               pass
       
       return ''
   
   def _is_timestamp(self, text: str) -> bool:
       """Check if text looks like a timestamp."""
       import re
       # Common timestamp patterns: "10:30 AM", "Yesterday", "12/31/2025"
       patterns = [
           r'^\d{1,2}:\d{2}\s*(AM|PM)?$',  # 10:30 AM
           r'^(Yesterday|Today)$',          # Yesterday, Today
           r'^\d{1,2}/\d{1,2}/\d{2,4}$',   # 12/31/25
           r'^\d{1,2}:\d{2}$'               # 10:30 (24-hour)
       ]
       return any(re.match(p, text, re.IGNORECASE) for p in patterns)
   
   def _is_sender_name(self, text: str) -> bool:
       """Check if text looks like a sender name (short, no punctuation)."""
       if len(text) > 50:  # Names are usually short
           return False
       if text.endswith(':') or text.endswith(','):  # Might be part of message
           return False
       # If it's all caps or title case and short, might be a name
       return text.isupper() or text.istitle()
   ```

**Expected Outcome:** Message text extracted correctly

---

### Fix #4: Update Chat Name Extraction

**Steps:**

1. **From DOM Inspector Output:**
   - Check section "### 6. CHAT NAME/CONTACT EXTRACTION ###"
   - Identify where chat names are located
   - Note if they use `title` attribute, `aria-label`, or inner text

2. **Implement Robust Name Extraction:**
   ```python
   def _extract_chat_name(self, chat_element) -> str:
       """Extract the chat/contact name from a chat item."""
       
       # Strategy 1: Look for span with title attribute
       try:
           title_span = chat_element.query_selector('span[title]')
           if title_span:
               title = title_span.get_attribute('title')
               if title and len(title) > 1:
                   self.logger.debug(f"Chat name from title: {title}")
                   return title
       except Exception:
               pass
       
       # Strategy 2: Look for element with aria-label
       try:
           aria_label = chat_element.get_attribute('aria-label')
           if aria_label:
               # Aria label format: "Chat Name, 3 messages, unread"
               # Extract just the name (usually before first comma)
               name = aria_label.split(',')[0].strip()
               if name and len(name) > 1:
                   self.logger.debug(f"Chat name from aria-label: {name}")
                   return name
       except Exception:
               pass
       
       # Strategy 3: Look for heading elements (h1, h2, h3)
       try:
           for tag in ['h1', 'h2', 'h3', 'h4']:
               heading = chat_element.query_selector(tag)
               if heading:
                   text = heading.inner_text().strip()
                   if text and len(text) < 100:  # Names are usually short
                       self.logger.debug(f"Chat name from {tag}: {text}")
                       return text
       except Exception:
               pass
       
       # Strategy 4: Get first text element that looks like a name
       try:
           all_spans = chat_element.query_selector_all('span')
           for span in all_spans[:5]:  # Check first few spans
               text = span.inner_text().strip()
               if text and 2 < len(text) < 50 and not self._is_timestamp(text):
                   # If it's the first substantial text, likely the name
                   self.logger.debug(f"Chat name from span: {text}")
                   return text
       except Exception:
               pass
       
       return 'Unknown'
   ```

**Expected Outcome:** Chat names extracted correctly

---

### Fix #5: Add Explicit Waiting and Retry Logic

**Steps:**

1. **Update `check_for_updates()` with Proper Waits:**
   ```python
   def check_for_updates(self) -> List[Dict[str, Any]]:
       """Check WhatsApp Web for new messages containing keywords."""
       
       # Ensure browser is initialized
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
           # Wait for chat list to be present (with timeout)
           try:
               self.logger.info("Waiting for chat list to load...")
               chat_list_selectors = [
                   '[data-testid="chat-list"]',
                   '[role="list"]',
                   '#pane-side'
               ]
               
               chat_list = None
               for selector in chat_list_selectors:
                   try:
                       chat_list = self.page.wait_for_selector(
                           selector, 
                           timeout=5000,
                           state='attached'
                       )
                       if chat_list:
                           self.logger.debug(f"Chat list found via: {selector}")
                           break
                   except Exception:
                       continue
               
               if not chat_list:
                   self.logger.warning("Chat list not found after waiting")
                   return []
                   
           except Exception as e:
               self.logger.error(f"Error waiting for chat list: {e}")
               return []
           
           # Small wait for content to stabilize
           time.sleep(1)
           
           messages = []
           
           # Scroll chat list to ensure all chats are loaded
           try:
               self.logger.debug("Scrolling chat list to load all chats...")
               chat_list.evaluate('el => { el.scrollTop = el.scrollHeight; }')
               time.sleep(0.5)
               chat_list.evaluate('el => { el.scrollTop = 0; }')
               time.sleep(0.5)
           except Exception as e:
               self.logger.debug(f"Could not scroll chat list: {e}")
           
           # Get all chat items
           try:
               chat_items = chat_list.query_selector_all('[role="listitem"]')
               self.logger.info(f"Found {len(chat_items)} chat items in chat list")
               
               # Process each chat
               for idx, chat in enumerate(chat_items[:50]):  # Limit to first 50
                   try:
                       message_data = self._extract_message_data(chat)
                       
                       if message_data and message_data.get('has_unread'):
                           self.logger.info(
                               f"🔔 Unread message detected from '{message_data['chat_name']}'"
                           )
                           
                           # Check for keywords
                           message_lower = message_data['message_text'].lower()
                           matched_keywords = [
                               kw for kw in self.keywords 
                               if kw in message_lower
                           ]
                           
                           if matched_keywords:
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
                   except Exception as e:
                       self.logger.debug(f"Error processing chat {idx}: {e}")
                       continue
                       
           except Exception as e:
               self.logger.error(f"Error finding chat items: {e}")
               return []
           
           if messages:
               self.logger.info(f"✅ Found {len(messages)} new matching message(s)")
           else:
               self.logger.info("No new matching messages found in this cycle")
           
           return messages
           
       except Exception as e:
           self.logger.error(f"Error checking WhatsApp messages: {e}", exc_info=True)
           return []
   ```

**Expected Outcome:** More reliable element detection with proper waits

---

### Fix #6: Add MutationObserver for Real-Time Detection

**Steps:**

1. **Add MutationObserver to `initialize_browser.py`:**
   ```python
   def InitializeBrowser(self) -> bool:
       # ... existing initialization code ...
       
       # After successful login, inject MutationObserver
       self.logger.info("Injecting MutationObserver for real-time updates...")
       try:
           self.page.evaluate("""
               window.whatsappNewMessages = [];
               
               const observer = new MutationObserver((mutations) => {
                   mutations.forEach(mutation => {
                       if (mutation.addedNodes.length > 0) {
                           mutation.addedNodes.forEach(node => {
                               if (node.nodeType === 1 && node.querySelector) {
                                   // Check if added node is a chat item or message
                                   const chatItem = node.closest('[role="listitem"]');
                                   if (chatItem) {
                                       window.whatsappNewMessages.push({
                                           type: 'new_chat_item',
                                           time: new Date().toISOString()
                                       });
                                   }
                                   
                                   // Check for unread indicators
                                   const unread = node.querySelector('[aria-label*="unread"], .Ep61I, .P1v7c');
                                   if (unread) {
                                       window.whatsappNewMessages.push({
                                           type: 'unread_indicator',
                                           time: new Date().toISOString()
                                       });
                                   }
                               }
                           });
                       }
                   });
               });
               
               // Observe chat list container
               const observeChatList = () => {
                   const chatList = document.querySelector('[data-testid="chat-list"], [role="list"]');
                   if (chatList) {
                       observer.observe(chatList, {
                           childList: true,
                           subtree: true,
                           attributes: true
                       });
                       console.log('MutationObserver attached to chat list');
                   } else {
                       setTimeout(observeChatList, 1000);
                   }
               };
               
               observeChatList();
           """)
           self.logger.info("MutationObserver injected successfully")
       except Exception as e:
           self.logger.warning(f"Could not inject MutationObserver: {e}")
       
       return True
   ```

2. **Check Mutation Log in `check_for_updates()`:**
   ```python
   # After getting chat items, check for mutations
   try:
       mutation_count = self.page.evaluate("""
           () => {
               const count = window.whatsappNewMessages ? window.whatsappNewMessages.length : 0;
               // Clear the log after reading
               if (window.whatsappNewMessages) {
                   window.whatsappNewMessages = [];
               }
               return count;
           }
       """)
       
       if mutation_count > 0:
           self.logger.info(f"🔔 MutationObserver detected {mutation_count} potential new message(s)")
   except Exception as e:
       self.logger.debug(f"Could not check mutation log: {e}")
   ```

**Expected Outcome:** Real-time detection of new messages

---

## Part 3: Testing Strategy

### Test 1: Selector Validation

**Purpose:** Verify all selectors work correctly

**Steps:**
1. Run `inspect_dom.py` while logged into WhatsApp
2. Compare output with current selectors in code
3. Update selectors based on actual DOM structure
4. Run watcher and verify it detects chat list

**Success Criteria:**
- Chat list container found
- Chat items enumerated correctly
- No selector errors in logs

---

### Test 2: Unread Message Detection

**Purpose:** Verify unread messages are detected

**Steps:**
1. Start WhatsApp Watcher
2. Send a test message from another device
3. Watch logs for detection
4. Verify action file is created if keyword matches

**Success Criteria:**
- Unread indicator detected within 30 seconds
- Correct chat name extracted
- Message text captured

---

### Test 3: Keyword Matching

**Purpose:** Verify keyword filtering works

**Steps:**
1. Send message with keyword "urgent" from another device
2. Send message without keywords
3. Verify only keyword-matching messages create action files

**Success Criteria:**
- Action file created for "urgent" message
- No action file for non-keyword message
- Correct keywords logged

---

### Test 4: Persistence Across Restarts

**Purpose:** Verify session persists and doesn't re-detect old messages

**Steps:**
1. Process some messages
2. Stop watcher (Ctrl+C)
3. Restart watcher
4. Verify old messages not re-processed

**Success Criteria:**
- Session restored (no QR code needed)
- Old messages not re-detected
- New messages detected correctly

---

### Test 5: Long-Running Stability

**Purpose:** Verify watcher runs stably for extended periods

**Steps:**
1. Start watcher
2. Leave running for 1+ hour
3. Send messages periodically
4. Check logs for errors or memory issues

**Success Criteria:**
- No crashes
- Consistent detection
- Browser memory stable (<500MB)

---

## Part 4: File Changes Required

### Files to Modify:

1. **`WhatsappWatcher/helpers/check_for_updates.py`**
   - Update chat list selector logic
   - Implement multi-strategy unread detection
   - Add robust message text extraction
   - Add robust chat name extraction
   - Add explicit waiting

2. **`WhatsappWatcher/helpers/initialize_browser.py`**
   - Add MutationObserver injection
   - Improve login detection

3. **`WhatsappWatcher/helpers/extract_message_data.py`** (Create New)
   - Extract `_extract_message_data()` from `check_for_updates.py`
   - Add helper methods: `_extract_chat_name()`, `_extract_message_text()`, `_check_unread_status()`
   - Add utility methods: `_is_timestamp()`, `_is_sender_name()`

4. **`WhatsappWatcher/inspect_dom.py`** (Create New - Already Created)
   - DOM inspection tool
   - Exports selectors to JSON

---

## Part 5: Quick Start Guide

### For Immediate Testing:

1. **Run DOM Inspector:**
   ```bash
   cd WhatsappWatcher
   uv run python inspect_dom.py
   ```
   - Scan QR code when prompted
   - Review output selectors
   - Send test message to see mutation detection

2. **Update Selectors:**
   - Based on `inspect_dom.py` output, update selectors in `check_for_updates.py`
   - Focus on sections marked with "### 2. CHAT LIST PANEL ###" and "### 4. UNREAD INDICATORS ###"

3. **Test Watcher:**
   ```bash
   uv run python main.py --vault ../vault --interval 10
   ```
   - Send test messages with keywords
   - Watch logs for detection
   - Verify action files created

4. **Review and Iterate:**
   - Check logs for errors
   - Adjust selectors if needed
   - Test with different message types (individual, group, with media)

---

## Part 6: Common Issues and Solutions

### Issue: "Chat list not found"

**Solution:**
- Check if logged in (QR code scanned)
- Verify WhatsApp Web fully loaded
- Try alternative selectors from DOM inspector output

---

### Issue: "No unread messages detected"

**Solution:**
- Check aria-label format in DOM inspector
- Look for green SVG indicators
- Verify unread badge class names
- Consider color-based detection as fallback

---

### Issue: "Message text is empty"

**Solution:**
- Check message preview element structure
- Look for nested spans
- Try getting all text and parsing
- Verify message isn't an image/media (no text)

---

### Issue: "Browser crashes frequently"

**Solution:**
- Set `PLAYWRIGHT_HEADLESS=false` for debugging
- Increase memory allocation
- Check for WhatsApp rate limiting
- Verify session files not corrupted

---

## Part 7: Future Improvements

### Enhancement #1: Webhook-Based Detection

Instead of polling, use WhatsApp Web's internal events:
```javascript
// Listen for WhatsApp's internal message events
window.addEventListener('message', (event) => {
    if (event.data.type === 'new_message') {
        // Trigger Python callback
    }
});
```

### Enhancement #2: Machine Learning Classification

Use ML to classify messages by urgency:
- Train on historical action files
- Predict priority level
- Auto-categorize messages

### Enhancement #3: Multi-Device Support

Support WhatsApp's multi-device beta:
- Handle linked devices
- Sync across sessions
- Better session management

---

## Conclusion

The WhatsApp Watcher failure is primarily due to WhatsApp Web's evolving DOM structure. By implementing the fixes above—particularly the multi-strategy detection for unread messages and robust element extraction—the watcher should reliably detect and process messages.

**Next Steps:**
1. Run `inspect_dom.py` to get current DOM structure
2. Update selectors in `check_for_updates.py`
3. Test with real messages
4. Iterate based on results

**Estimated Time to Fix:** 2-4 hours (including testing)

**Risk Level:** Low (changes are isolated to WhatsApp watcher)

**Dependencies:** None (uses existing Playwright infrastructure)
