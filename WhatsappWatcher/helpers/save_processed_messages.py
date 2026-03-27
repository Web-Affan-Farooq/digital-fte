import json
import datetime

def SaveProcessedMessages(self) -> None:
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