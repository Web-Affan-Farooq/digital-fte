import json

def LoadProcessedMessages(self) -> None:
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