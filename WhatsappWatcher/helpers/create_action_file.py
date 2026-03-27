from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

def CreateActionFile(self, item: Dict[str, Any]) -> Optional[Path]:
    """
    Create a markdown action file for a WhatsApp message.

    Args:
        self: WhatsAppWatcher instance
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
