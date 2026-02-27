"""
File System Watcher for Digital FTE

This script monitors a drop folder for new files and creates
actionable markdown files in the Obsidian vault.

Use Cases:
- Drop PDFs for processing
- Drop invoices for accounting
- Drop documents for summarization
- Drop any file that needs AI attention

Usage:
    python scripts/filesystem_watcher.py
    
Environment Variables:
    DROP_FOLDER_PATH: Path to monitor (default: ./vault/Inbox/Drop)
    VAULT_PATH: Path to Obsidian vault (default: ./vault)
    DRY_RUN: Set to 'false' to enable actual processing
    CHECK_INTERVAL: Seconds between checks (default: 30)
"""

import hashlib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from base_watcher import BaseWatcher

# Watchdog imports (optional, graceful fallback)
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Define dummy class for fallback
    class FileSystemEventHandler:
        pass
    Observer = None
    print("Watchdog not installed. Install with: pip install watchdog")
    print("Filesystem watcher will use polling mode instead.\n")


class DropFolderHandler(FileSystemEventHandler):
    """
    Handles file system events in the drop folder.
    
    Attributes:
        watcher: Parent FilesystemWatcher instance
        processed_files: Set of processed file hashes
    """

    def __init__(self, watcher: 'FilesystemWatcher'):
        """
        Initialize the handler.
        
        Args:
            watcher: Parent FilesystemWatcher instance
        """
        super().__init__()
        self.watcher = watcher
        self.processed_files: set = set()

    def on_created(self, event):
        """
        Handle file creation events.
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
        
        source_path = Path(event.src_path)
        
        # Skip hidden files and temp files
        if source_path.name.startswith('.') or source_path.suffix.endswith('.tmp'):
            return
        
        self.watcher.logger.info(f"File created: {source_path}")
        self.watcher.process_file(source_path)


class FilesystemWatcher(BaseWatcher):
    """
    Watches a drop folder for new files and creates action files.
    
    Attributes:
        drop_folder: Path to the monitored drop folder
        observer: Watchdog Observer instance (if available)
    """

    def __init__(
        self,
        vault_path: str,
        drop_folder: Optional[str] = None,
        check_interval: int = 30,
        use_watchdog: bool = True
    ):
        """
        Initialize the filesystem watcher.

        Args:
            vault_path: Path to the Obsidian vault
            drop_folder: Path to the drop folder (default: vault/Inbox/Drop)
            check_interval: Seconds between checks (default: 30)
            use_watchdog: Use watchdog for real-time monitoring (default: True)
        """
        super().__init__(vault_path, check_interval)

        # Set up drop folder
        if drop_folder:
            self.drop_folder = Path(drop_folder)
        else:
            self.drop_folder = self.inbox / 'Drop'
        
        # Ensure drop folder exists
        self.drop_folder.mkdir(parents=True, exist_ok=True)
        
        # Use watchdog if available and requested
        self.use_watchdog = use_watchdog and WATCHDOG_AVAILABLE
        self.observer = None
        
        # Track processed files by hash
        self.processed_files: set = set()
        self._load_processed_files()

    def _load_processed_files(self) -> None:
        """Load previously processed file hashes from disk."""
        cache_file = self.logs / 'filesystem_processed_hashes.txt'
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.processed_files = set(line.strip() for line in f if line.strip())
                self.logger.info(f"Loaded {len(self.processed_files)} previously processed file hashes")
            except Exception as e:
                self.logger.warning(f"Could not load processed hashes: {e}")
                self.processed_files = set()
        else:
            self.processed_files = set()

    def _save_processed_files(self) -> None:
        """Save processed file hashes to disk."""
        cache_file = self.logs / 'filesystem_processed_hashes.txt'
        try:
            with open(cache_file, 'w') as f:
                for file_hash in self.processed_files:
                    f.write(f"{file_hash}\n")
            self.logger.debug(f"Saved {len(self.processed_files)} processed file hashes")
        except Exception as e:
            self.logger.error(f"Could not save processed hashes: {e}")

    def _calculate_file_hash(self, filepath: Path) -> str:
        """
        Calculate SHA256 hash of a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            SHA256 hash hex string
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_file_metadata(self, filepath: Path) -> Dict[str, Any]:
        """
        Get metadata about a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Dictionary of file metadata
        """
        stat = filepath.stat()
        
        # File type categories
        file_type = "unknown"
        file_category = "other"
        
        extension_map = {
            '.pdf': ('PDF Document', 'document'),
            '.doc': ('Word Document', 'document'),
            '.docx': ('Word Document', 'document'),
            '.txt': ('Text File', 'document'),
            '.md': ('Markdown File', 'document'),
            '.xls': ('Excel Spreadsheet', 'spreadsheet'),
            '.xlsx': ('Excel Spreadsheet', 'spreadsheet'),
            '.csv': ('CSV File', 'spreadsheet'),
            '.jpg': ('JPEG Image', 'image'),
            '.jpeg': ('JPEG Image', 'image'),
            '.png': ('PNG Image', 'image'),
            '.gif': ('GIF Image', 'image'),
            '.zip': ('ZIP Archive', 'archive'),
            '.rar': ('RAR Archive', 'archive'),
            '.7z': ('7-Zip Archive', 'archive'),
            '.mp3': ('MP3 Audio', 'media'),
            '.mp4': ('MP4 Video', 'media'),
            '.wav': ('WAV Audio', 'media'),
        }
        
        if filepath.suffix.lower() in extension_map:
            file_type, file_category = extension_map[filepath.suffix.lower()]
        
        return {
            'name': filepath.name,
            'size': stat.st_size,
            'size_human': self._format_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'extension': filepath.suffix.lower(),
            'file_type': file_type,
            'file_category': file_category,
            'hash': self._calculate_file_hash(filepath)
        }

    def _format_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Human-readable size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def check_for_updates(self) -> List[Path]:
        """
        Check drop folder for new files (polling method).

        Returns:
            List of new file paths
        """
        new_files = []

        try:
            for filepath in self.drop_folder.iterdir():
                if filepath.is_file() and not filepath.name.startswith('.'):
                    file_hash = self._calculate_file_hash(filepath)
                    if file_hash not in self.processed_files:
                        new_files.append(filepath)

            return new_files

        except Exception as e:
            self.logger.error(f"Error checking drop folder: {e}")
            return []

    def create_action_file(self, filepath: Path) -> Optional[Path]:
        """
        Create a markdown action file for a dropped file.
        
        This is the required abstract method from BaseWatcher.
        Delegates to process_file for actual implementation.

        Args:
            filepath: Path to the file
            
        Returns:
            Path to created action file, or None if failed
        """
        return self.process_file(filepath)

    def process_file(self, filepath: Path) -> Optional[Path]:
        """
        Process a single file and create an action file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Path to created action file, or None if failed
        """
        try:
            # Calculate hash and check if already processed
            file_hash = self._calculate_file_hash(filepath)
            if file_hash in self.processed_files:
                self.logger.debug(f"File already processed: {filepath}")
                return None
            
            # Get metadata
            metadata = self._get_file_metadata(filepath)
            
            # Determine priority based on file type and name
            priority = self.get_priority(f"{filepath.name} {metadata['file_type']}")
            
            # Sanitize filename
            safe_name = self.sanitize_filename(filepath.stem)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            action_filename = f"FILE_{safe_name}_{timestamp}.md"
            
            # Create content
            content = f"""---
type: file_drop
original_name: {metadata['name']}
file_type: {metadata['file_type']}
file_category: {metadata['file_category']}
size: {metadata['size_human']} ({metadata['size']} bytes)
extension: {metadata['extension']}
created: {metadata['created']}
modified: {metadata['modified']}
priority: {priority}
status: pending
file_hash: {file_hash}
---

# File Drop: {metadata['name']}

## File Information

| Property | Value |
|----------|-------|
| **Type** | {metadata['file_type']} |
| **Category** | {metadata['file_category']} |
| **Size** | {metadata['size_human']} |
| **Created** | {metadata['created']} |
| **Modified** | {metadata['modified']} |

## Priority
{priority.upper()}

---

## Location

**Source:** `{filepath}`

**Copied to:** `{self.needs_action / filepath.name}`

---

## Suggested Actions

Based on file type:

### For Documents (.pdf, .doc, .txt)
- [ ] Read and summarize content
- [ ] Extract key information
- [ ] Identify required actions
- [ ] Archive after processing

### For Spreadsheets (.xls, .xlsx, .csv)
- [ ] Review data contents
- [ ] Update accounting records (if financial)
- [ ] Extract relevant metrics
- [ ] Archive after processing

### For Images
- [ ] Review image content
- [ ] Extract text (OCR) if needed
- [ ] Add to appropriate project folder
- [ ] Archive after processing

### For Archives (.zip, .rar)
- [ ] Extract contents
- [ ] Review extracted files
- [ ] Process individual files
- [ ] Archive after processing

---

## Notes

_Add your notes here_

---

## Processing Log

- **Detected:** {datetime.now().isoformat()}
- **Priority:** {priority}
- **Status:** Pending review

"""
            
            # Copy file to needs_action folder
            dest_path = self.needs_action / filepath.name
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would copy: {filepath} -> {dest_path}")
                self.logger.info(f"[DRY RUN] Would create: {self.needs_action / action_filename}")
                self.log_action('file_detected', {
                    'name': metadata['name'],
                    'type': metadata['file_type'],
                    'size': metadata['size_human'],
                    'priority': priority
                })
            else:
                # Copy file
                shutil.copy2(filepath, dest_path)
                self.logger.info(f"Copied file: {filepath} -> {dest_path}")
                
                # Write action file
                action_path = self.needs_action / action_filename
                action_path.write_text(content, encoding='utf-8')
                self.logger.info(f"Created action file: {action_path}")
                
                # Mark as processed
                self.processed_files.add(file_hash)
                self._save_processed_files()
                
                self.log_action('file_action_created', {
                    'name': metadata['name'],
                    'type': metadata['file_type'],
                    'size': metadata['size_human'],
                    'priority': priority,
                    'filepath': str(action_path)
                })
                
                # Optionally remove original from drop folder
                # filepath.unlink()  # Uncomment to auto-clean drop folder
            
            return dest_path
            
        except Exception as e:
            self.logger.error(f"Error processing file: {e}")
            return None

    def start_observer(self) -> None:
        """
        Start the watchdog observer for real-time monitoring.
        """
        if not self.use_watchdog:
            self.logger.warning("Watchdog not available, using polling mode")
            return
        
        if not WATCHDOG_AVAILABLE:
            self.logger.warning("Watchdog library not installed, using polling mode")
            self.use_watchdog = False
            return

        try:
            event_handler = DropFolderHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, str(self.drop_folder), recursive=False)
            self.observer.start()
            self.logger.info(f"Watchdog observer started for: {self.drop_folder}")
        except Exception as e:
            self.logger.error(f"Could not start watchdog observer: {e}")
            self.use_watchdog = False

    def stop_observer(self) -> None:
        """
        Stop the watchdog observer.
        """
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("Watchdog observer stopped")

    def run(self) -> None:
        """
        Main run loop for the filesystem watcher.
        
        Uses watchdog for real-time monitoring if available,
        otherwise falls back to polling.
        """
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Vault path: {self.vault_path}")
        self.logger.info(f"Drop folder: {self.drop_folder}")
        self.logger.info(f"Check interval: {self.check_interval}s")
        self.logger.info(f"Dry run mode: {self.dry_run}")
        self.logger.info(f"Use watchdog: {self.use_watchdog}")
        
        # Start watchdog observer if available
        if self.use_watchdog:
            self.start_observer()
        
        try:
            if self.use_watchdog:
                # Watchdog mode - just keep running
                while True:
                    import time
                    time.sleep(self.check_interval)
            else:
                # Polling mode - use parent implementation
                super().run()
                
        except KeyboardInterrupt:
            self.logger.info(f"{self.__class__.__name__} stopped by user")
        finally:
            self.stop_observer()


def main():
    """Main entry point for filesystem watcher."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Filesystem Watcher for Digital FTE')
    parser.add_argument(
        '--vault',
        type=str,
        default=os.getenv('VAULT_PATH', './vault'),
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--drop-folder',
        type=str,
        default=os.getenv('DROP_FOLDER_PATH'),
        help='Path to drop folder to monitor'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=int(os.getenv('CHECK_INTERVAL', '30')),
        help='Check interval in seconds'
    )
    parser.add_argument(
        '--no-watchdog',
        action='store_true',
        help='Disable watchdog even if available'
    )
    
    args = parser.parse_args()
    
    print("📁 Filesystem Watcher")
    print("=" * 50)
    print(f"Vault: {args.vault}")
    print(f"Drop folder: {args.drop_folder or './vault/Inbox/Drop'}")
    print(f"Check interval: {args.interval}s")
    print(f"Dry run: {os.getenv('DRY_RUN', 'true')}")
    print(f"Watchdog: {not args.no_watchdog and WATCHDOG_AVAILABLE}")
    print("\nStarting watcher... (Press Ctrl+C to stop)\n")
    print(f"Drop files into: {Path(args.vault) / 'Inbox' / 'Drop'}\n")
    
    try:
        watcher = FilesystemWatcher(
            vault_path=args.vault,
            drop_folder=args.drop_folder,
            check_interval=args.interval,
            use_watchdog=not args.no_watchdog
        )
        watcher.run()
    except KeyboardInterrupt:
        print("\n\n👋 Watcher stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
