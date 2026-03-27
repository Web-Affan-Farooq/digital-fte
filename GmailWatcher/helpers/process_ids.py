def LoadProcessedIds(self) -> None:
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

def SaveProcessedIds(self) -> None:
    """Save processed message IDs to disk."""
    cache_file = self.logs / 'gmail_processed_ids.txt'
    try:
        with open(cache_file, 'w') as f:
            for msg_id in self.processed_ids:
                f.write(f"{msg_id}\n")
        self.logger.debug(f"Saved {len(self.processed_ids)} processed message IDs")
    except Exception as e:
        self.logger.error(f"Could not save processed IDs: {e}")