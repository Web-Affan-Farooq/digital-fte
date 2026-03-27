import time
from . import InitializeBrowser

def RunWatcher(self) -> None:
    """
    Main run loop for the WhatsApp watcher.
    
    Key improvements:
    - Browser initializes ONCE at startup
    - Browser stays open across all check cycles
    - No page reloads - relies on WhatsApp's real-time push updates
    - Only reinitializes browser if it actually dies
    """
    self.logger.info(f"Starting {self.__class__.__name__}")
    self.logger.info(f"Vault path: {self.vault_path}")
    self.logger.info(f"Session path: {self.session_path}")
    self.logger.info(f"Check interval: {self.check_interval}s")
    self.logger.info(f"Dry run mode: {self.dry_run}")
    self.logger.info(f"Keywords: {self.keywords}")
    self.logger.info("=" * 60)

    browser_initialized = False
    
    try:
        # Initialize browser ONCE at startup
        self.logger.info("Initializing browser (this happens only once)...")
        if InitializeBrowser(self):
            browser_initialized = True
            self.logger.info("✅ Browser initialized successfully")
            self.logger.info("💡 Tip: Browser will stay open for real-time updates")
        else:
            self.logger.error("❌ Failed to initialize browser. Exiting.")
            return

        # Main monitoring loop
        cycle_count = 0
        
        while True:
            cycle_count += 1
            self.logger.debug(f"--- Check cycle {cycle_count} ---")
            
            try:
                # Check for new messages (no page reload - real-time updates)
                items = self.check_for_updates()

                if items:
                    self.logger.info(f"📬 Found {len(items)} new message(s) matching keywords")

                    for item in items:
                        if self.dry_run:
                            self.logger.info(
                                f"  [DRY RUN] Would process message from {item['chat_name']}: " +
                                f"{item['message_text'][:50]}..."
                            )
                        else:
                            filepath = self.create_action_file(item)
                            if filepath:
                                self.logger.info(f"  ✅ Created: {filepath.name}")
                else:
                    self.logger.debug("No new matching messages")

            except Exception as e:
                self.logger.error(f"Error in check cycle: {e}")
                # Don't immediately reinitialize - wait for next cycle
                # The check_for_updates will handle browser health checks
            
            # Wait before next check
            if cycle_count % 10 == 0:
                self.logger.info(f"Still monitoring... ({cycle_count} cycles completed)")
            
            time.sleep(self.check_interval)

    except KeyboardInterrupt:
        self.logger.info(f"\n👋 {self.__class__.__name__} stopped by user")
    except Exception as e:
        self.logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup: close browser when watcher stops
        self.logger.info("Closing browser...")
        if browser_initialized:
            self._close_browser()
        self.logger.info("Watcher stopped gracefully")
