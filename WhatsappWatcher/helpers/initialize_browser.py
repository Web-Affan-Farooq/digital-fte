import os
import time

def InitializeBrowser(self) -> bool:
    """
    Initialize the browser and navigate to WhatsApp Web.
    
    This should only be called once at startup, not on every check cycle.
    The browser session persists across check cycles.

    Args:
        self: WhatsAppWatcher instance

    Returns:
        True if successful
    """
    try:
        from playwright.sync_api import sync_playwright

        # Only initialize if not already running
        if self.browser_context is not None:
            try:
                # Check if browser is still alive
                self.page.title()
                self.logger.info("Browser already running, skipping re-initialization")
                return True
            except Exception:
                self.logger.warning("Browser died, reinitializing...")
                self._close_browser()

        self.playwright = sync_playwright().start()

        headless = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
        
        self.logger.info(f"Launching browser (headless={headless})...")

        # Launch persistent browser context with session storage
        self.browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_path),
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--start-maximized' if not headless else ''
            ]
        )

        self.page = self.browser_context.pages[0] if self.browser_context.pages else self.browser_context.new_page()
        
        # Set viewport size
        self.page.set_viewport_size({"width": 1280, "height": 720})

        # Navigate to WhatsApp Web
        self.logger.info("Navigating to WhatsApp Web...")
        self.page.goto('https://web.whatsapp.com', wait_until='networkidle', timeout=60000)

        # Wait for page to fully load
        self.logger.info("Waiting for WhatsApp Web to load...")
        time.sleep(10)

        # Debug: Log current page state
        try:
            current_url = self.page.url
            page_title = self.page.title()
            self.logger.debug(f"Page loaded - URL: {current_url}, Title: {page_title}")
        except Exception as e:
            self.logger.debug(f"Could not get page info: {e}")

        # Check if logged in or needs QR code
        is_logged_in = self._check_if_logged_in()
        self.logger.info(f"Login status check result: {'Logged in' if is_logged_in else 'Not logged in'}")

        if not is_logged_in:
            self.logger.warning("⚠️  QR Code scan required!")
            self.logger.info("Please scan the QR code with WhatsApp on your phone.")
            self.logger.info("Waiting up to 60 seconds for QR code scan...")

            # Wait for login (QR code scan)
            try:
                self.page.wait_for_selector('[data-testid="chat-list"]', timeout=60000)
                self.logger.info("✅ QR code scanned successfully!")
            except Exception:
                self.logger.error("QR code scan timed out. Restart the watcher to try again.")
                return False

        # Final verification
        if not self._check_if_logged_in():
            self.logger.error("Failed to log in to WhatsApp Web")
            return False

        self.logger.info("✅ WhatsApp Web logged in successfully")
        
        # Give WhatsApp time to fully load messages
        time.sleep(5)
        
        return True

    except Exception as e:
        self.logger.error(f"Failed to initialize browser: {e}")
        if self.playwright:
            self._close_browser()
        return False


