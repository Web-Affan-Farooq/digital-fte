# Gmail API imports (optional, graceful fallback)
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("Gmail API libraries not installed. Install with:")
    print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")


def Authenticate(self) -> bool:
    """
    Authenticate with Gmail API.
    
    Returns:
        True if authentication successful, False otherwise
    """
    creds = None
    
    # Load existing token
    if self.token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                self.token_path, self.SCOPES
            )
        except Exception as e:
            self.logger.warning(f"Could not load token: {e}")
            creds = None
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                self.logger.warning("Token refresh failed, re-authenticating")
                creds = None
        
        if not creds:
            if not self.credentials_path.exists():
                self.logger.error(
                    f"Credentials file not found: {self.credentials_path}\n"
                    f"Please download credentials.json from Google Cloud Console and place it there."
                )
                return False
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                
                # Save token
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                
                self.logger.info("Authentication successful")
            except Exception as e:
                self.logger.error(f"Authentication failed: {e}")
                return False
    
    # Build service
    try:
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    except Exception as e:
        self.logger.error(f"Could not build Gmail service: {e}")
        return False