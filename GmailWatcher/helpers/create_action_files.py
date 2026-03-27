from pathlib import Path
from typing import Dict , Optional , Any 
from datetime import datetime

def CreateActionFiles(self, item: Dict[str, Any]) -> Optional[Path]:
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
- [ ] Don't respond to this email 
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