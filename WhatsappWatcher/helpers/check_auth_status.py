def CheckIfLoggedIn(self) -> bool:
    """
    Check if WhatsApp Web is logged in by looking for the chat list.

    Returns:
        True if logged in, False otherwise
    """
    try:
        # First, check for QR code (not logged in) - quick check
        qr_selectors = [
            '[data-testid="qr-point"]',
            'canvas[data-testid="qr"]',
            '[data-testid="qr-default"]',
            '#qr'
        ]

        for selector in qr_selectors:
            try:
                element = self.page.query_selector(selector)
                if element:
                    self.logger.debug(f"QR code detected via {selector}")
                    return False
            except Exception:
                continue

        # Multiple selectors to check for logged-in state
        # Use query_selector first (immediate), then wait_for_selector as fallback
        logged_in_selectors = [
            '[data-testid="chat-list"]',           # Main chat list container
            '[data-asset-testid="chat-list"]',     # Alternative chat list
            'div[role="list"]',                     # Chat list role
            '[data-testid="default-user"]',        # Default user view
            '[title="Status"]',                     # Status tab
            '[title="New chat"]',                   # New chat button
            '[data-testid="chat-list-panel"]',     # Chat list panel
            '#pane-side',                          # Left sidebar (logged in)
        ]

        # First pass: quick check with query_selector (no waiting)
        for selector in logged_in_selectors:
            try:
                element = self.page.query_selector(selector)
                if element:
                    self.logger.debug(f"Logged in state detected via {selector}")
                    return True
            except Exception:
                continue

        # Second pass: wait briefly for dynamic content
        for selector in ['[data-testid="chat-list"]', 'div[role="list"]']:
            try:
                element = self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    self.logger.debug(f"Logged in state detected (after wait) via {selector}")
                    return True
            except Exception:
                continue

        # Fallback: check if we're on WhatsApp Web and no QR code is present
        # If URL is correct and no QR, likely logged in but still loading
        current_url = self.page.url
        if 'web.whatsapp.com' in current_url:
            self.logger.debug("On WhatsApp Web URL, assuming logged in (no QR detected)")
            return True

        return False

    except Exception as e:
        self.logger.debug(f"Error checking login status: {e}")
        return False
