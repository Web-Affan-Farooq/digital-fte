def CloseBrowser(self) -> None:
    """Close the browser."""
    if self.browser_context:
        try:
            self.browser_context.close()
        except Exception:
            pass
        self.browser_context = None
    
    if self.playwright:
        try:
            self.playwright.stop()
        except Exception:
            pass
        self.playwright = None
    
    self.page = None