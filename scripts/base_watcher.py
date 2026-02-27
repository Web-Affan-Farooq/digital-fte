"""
Base Watcher Template for Digital FTE

This module provides the abstract base class for all watcher scripts.
Watchers monitor external inputs (Gmail, WhatsApp, filesystems) and
create actionable markdown files in the Obsidian vault.

Usage:
    class MyWatcher(BaseWatcher):
        def check_for_updates(self) -> list:
            # Return list of new items to process
            pass

        def create_action_file(self, item) -> Path:
            # Create .md file in Needs_Action folder
            pass
"""

import logging
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseWatcher(ABC):
    """
    Abstract base class for all Digital FTE watchers.
    
    Attributes:
        vault_path: Path to the Obsidian vault root
        check_interval: Seconds between checks (default: 60)
        logger: Configured logger for the watcher
    """

    def __init__(self, vault_path: str, check_interval: int = 60):
        """
        Initialize the base watcher.

        Args:
            vault_path: Path to the Obsidian vault directory
            check_interval: How often to check for updates (in seconds)
        """
        self.vault_path = Path(vault_path)
        self.check_interval = check_interval
        
        # Folder paths
        self.inbox = self.vault_path / 'Inbox'
        self.needs_action = self.vault_path / 'Needs_Action'
        self.done = self.vault_path / 'Done'
        self.logs = self.vault_path / 'Logs'
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Track processed items to avoid duplicates
        self.processed_ids: set = set()
        
        # Dry run mode (from environment)
        import os
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for folder in [self.inbox, self.needs_action, self.done, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> logging.Logger:
        """
        Configure logging for the watcher.
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # File handler (daily rotating)
        log_file = self.logs / f'watcher_{datetime.now().strftime("%Y-%m-%d")}.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger

    @abstractmethod
    def check_for_updates(self) -> List[Any]:
        """
        Check for new items to process.
        
        Returns:
            List of new items (emails, messages, files, etc.)
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.check_for_updates() must be implemented"
        )

    @abstractmethod
    def create_action_file(self, item: Any) -> Optional[Path]:
        """
        Create a markdown action file for an item.
        
        Args:
            item: The item to create an action file for
            
        Returns:
            Path to the created file, or None if creation failed
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.create_action_file() must be implemented"
        )

    def get_priority(self, content: str) -> str:
        """
        Determine priority based on content keywords.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Priority level: 'critical', 'high', 'normal', or 'low'
        """
        content_lower = content.lower()
        
        # Critical keywords
        critical_keywords = ['urgent', 'asap', 'emergency', 'help', 'critical']
        if any(kw in content_lower for kw in critical_keywords):
            return 'critical'
        
        # High keywords
        high_keywords = ['invoice', 'payment', 'deadline', 'due', 'important']
        if any(kw in content_lower for kw in high_keywords):
            return 'high'
        
        # Low keywords
        low_keywords = ['newsletter', 'unsubscribe', 'promotion', 'offer']
        if any(kw in content_lower for kw in low_keywords):
            return 'low'
        
        return 'normal'

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string for use as a filename.
        
        Args:
            name: The original name
            
        Returns:
            Sanitized filename-safe string
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|？*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Limit length
        return name[:100] if len(name) > 100 else name

    def log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """
        Log an action to the daily log file.
        
        Args:
            action_type: Type of action (e.g., 'email_received', 'file_created')
            details: Dictionary of action details
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'actor': self.__class__.__name__,
            'details': details,
            'dry_run': self.dry_run
        }
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would log: {log_entry}")
        else:
            self.logger.debug(f"Logged action: {log_entry}")

    def run(self) -> None:
        """
        Main run loop for the watcher.
        
        Continuously checks for updates and creates action files.
        Runs until interrupted (Ctrl+C).
        """
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Vault path: {self.vault_path}")
        self.logger.info(f"Check interval: {self.check_interval}s")
        self.logger.info(f"Dry run mode: {self.dry_run}")
        
        try:
            while True:
                try:
                    # Check for new items
                    items = self.check_for_updates()
                    
                    if items:
                        self.logger.info(f"Found {len(items)} new item(s)")
                        
                        for item in items:
                            if self.dry_run:
                                self.logger.info(f"[DRY RUN] Would process item")
                            else:
                                filepath = self.create_action_file(item)
                                if filepath:
                                    self.logger.info(f"Created action file: {filepath}")
                    else:
                        self.logger.debug("No new items found")
                    
                except Exception as e:
                    self.logger.error(f"Error processing items: {e}", exc_info=True)
                
                # Wait before next check
                import time
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info(f"{self.__class__.__name__} stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    # Example usage (for testing)
    print("BaseWatcher is an abstract class. Subclass it to create a watcher.")
    print("\nExample:")
    print("""
class MyWatcher(BaseWatcher):
    def check_for_updates(self) -> list:
        # Your implementation here
        return []
    
    def create_action_file(self, item) -> Path:
        # Your implementation here
        pass
""")
