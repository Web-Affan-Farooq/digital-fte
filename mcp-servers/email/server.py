"""
Email MCP Server for Digital FTE

Provides email sending, drafting, and searching capabilities via Gmail API.
Built using FastMCP framework.

Usage:
    # Start server with stdio transport (for Claude Code)
    uv run python mcp-servers/email/server.py
    
    # Start server with HTTP transport
    uv run python mcp-servers/email/server.py --transport http --port 8801

Environment Variables:
    GMAIL_CREDENTIALS_PATH: Path to Gmail OAuth credentials
    GMAIL_TOKEN_PATH: Path to OAuth token (auto-generated)
    DRY_RUN: Set to 'true' to log emails without sending
"""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastmcp import FastMCP

# Gmail API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# from config import dry_run
import os
dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'

# ===========================================
# Server Configuration
# ===========================================

mcp = FastMCP(
    name="Digital FTE Email Server",
    # dependencies=["google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"],
)

# Global service instance
_gmail_service = None


# ===========================================
# Gmail Authentication
# ===========================================

def get_credentials_path() -> Path:
    """Get path to Gmail credentials file."""
    home = Path.home()
    gmail_dir = home / '.gmail_watcher'
    gmail_dir.mkdir(parents=True, exist_ok=True)
    
    creds_path = os.getenv('GMAIL_CREDENTIALS_PATH', gmail_dir / 'credentials.json')
    token_path = os.getenv('GMAIL_TOKEN_PATH', gmail_dir / 'token.json')
    
    return Path(creds_path), Path(token_path)


def authenticate_gmail() -> Optional[Any]:
    """
    Authenticate with Gmail API and return service instance.
    
    Returns:
        Gmail API service instance or None if authentication fails
    """
    global _gmail_service
    
    if _gmail_service is not None:
        return _gmail_service
    
    creds_path, token_path = get_credentials_path()
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    creds = None
    
    # Load existing token
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            print(f"Could not load token: {e}")
            creds = None
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds:
            if not creds_path.exists():
                print(f"Credentials file not found: {creds_path}")
                print("Please download credentials.json from Google Cloud Console")
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save token
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                
                print("Authentication successful")
            except Exception as e:
                print(f"Authentication failed: {e}")
                return None
    
    # Build service
    try:
        _gmail_service = build('gmail', 'v1', credentials=creds)
        return _gmail_service
    except Exception as e:
        print(f"Could not build Gmail service: {e}")
        return None


# ===========================================
# MCP Tools
# ===========================================

@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    html: bool = False
) -> Dict[str, Any]:
    """
    Send an email via Gmail.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        from_email: Sender email (optional, uses authenticated account)
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
        html: Whether body is HTML (default: False)
    
    Returns:
        Dictionary with status and message_id or error
    """    
    if dry_run:
        return {
            'status': 'dry_run',
            'message': 'Email not sent (DRY_RUN mode)',
            'details': {
                'to': to,
                'subject': subject,
                'from': from_email or 'authenticated_account',
                'cc': cc,
                'bcc': bcc
            }
        }
    
    # Authenticate
    service = authenticate_gmail()
    if not service:
        return {
            'status': 'error',
            'message': 'Failed to authenticate with Gmail API'
        }
    
    try:
        # Create message
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['from'] = from_email or 'me'
        message['subject'] = subject
        
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        
        # Add body
        if html:
            message.attach(MIMEText(body, 'html'))
        else:
            message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return {
            'status': 'success',
            'message_id': sent_message['id'],
            'thread_id': sent_message['threadId']
        }
        
    except HttpError as error:
        return {
            'status': 'error',
            'message': f'Gmail API error: {error}',
            'error_details': str(error)
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to send email: {e}',
            'error_details': str(e)
        }


@mcp.tool()
def draft_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    cc: Optional[str] = None,
    html: bool = False
) -> Dict[str, Any]:
    """
    Create a draft email in Gmail (does not send).
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        from_email: Sender email (optional)
        cc: CC recipients (comma-separated)
        html: Whether body is HTML (default: False)
    
    Returns:
        Dictionary with draft_id and status
    """
    # Authenticate
    service = authenticate_gmail()
    if not service:
        return {
            'status': 'error',
            'message': 'Failed to authenticate with Gmail API'
        }
    
    try:
        # Create message
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['from'] = from_email or 'me'
        message['subject'] = subject
        
        if cc:
            message['cc'] = cc
        
        # Add body
        if html:
            message.attach(MIMEText(body, 'html'))
        else:
            message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Create draft
        draft = service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw_message}}
        ).execute()
        
        return {
            'status': 'success',
            'draft_id': draft['id'],
            'message_id': draft['message']['id'],
            'action': 'draft_created_awaiting_review'
        }
        
    except HttpError as error:
        return {
            'status': 'error',
            'message': f'Gmail API error: {error}',
            'error_details': str(error)
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to create draft: {e}',
            'error_details': str(e)
        }


@mcp.tool()
def search_emails(
    query: str,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search emails in Gmail.
    
    Args:
        query: Gmail search query (e.g., "is:unread", "from:example@gmail.com")
        max_results: Maximum number of results (default: 10)
    
    Returns:
        Dictionary with list of matching emails
    """
    # Authenticate
    service = authenticate_gmail()
    if not service:
        return {
            'status': 'error',
            'message': 'Failed to authenticate with Gmail API'
        }
    
    try:
        # Search
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return {
                'status': 'success',
                'count': 0,
                'emails': [],
                'message': 'No emails found'
            }
        
        # Fetch details for each message
        emails = []
        for msg in messages:
            full_msg = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'To', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in full_msg['payload']['headers']}
            
            emails.append({
                'id': msg['id'],
                'thread_id': full_msg['threadId'],
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'subject': headers.get('Subject', ''),
                'date': headers.get('Date', ''),
                'snippet': full_msg.get('snippet', '')
            })
        
        return {
            'status': 'success',
            'count': len(emails),
            'emails': emails
        }
        
    except HttpError as error:
        return {
            'status': 'error',
            'message': f'Gmail API error: {error}',
            'error_details': str(error)
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to search emails: {e}',
            'error_details': str(e)
        }


@mcp.tool()
def get_email_content(
    message_id: str
) -> Dict[str, Any]:
    """
    Get full content of a specific email.
    
    Args:
        message_id: Gmail message ID
    
    Returns:
        Dictionary with email content and attachments info
    """
    # Authenticate
    service = authenticate_gmail()
    if not service:
        return {
            'status': 'error',
            'message': 'Failed to authenticate with Gmail API'
        }
    
    try:
        # Fetch full message
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        # Extract headers
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extract body
        body = ''
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        # Check for attachments
        attachments = []
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['filename']:
                    attachments.append({
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'size': part['body'].get('size', 0)
                    })
        
        return {
            'status': 'success',
            'id': message['id'],
            'thread_id': message['threadId'],
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'body': body,
            'attachments': attachments
        }
        
    except HttpError as error:
        return {
            'status': 'error',
            'message': f'Gmail API error: {error}',
            'error_details': str(error)
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to get email: {e}',
            'error_details': str(e)
        }


@mcp.tool()
def mark_as_read(message_id: str) -> Dict[str, Any]:
    """
    Mark an email as read.
    
    Args:
        message_id: Gmail message ID
    
    Returns:
        Dictionary with status
    """
    # Authenticate
    service = authenticate_gmail()
    if not service:
        return {
            'status': 'error',
            'message': 'Failed to authenticate with Gmail API'
        }
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return {
            'status': 'success',
            'message': f'Message {message_id} marked as read'
        }
        
    except HttpError as error:
        return {
            'status': 'error',
            'message': f'Gmail API error: {error}',
            'error_details': str(error)
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to mark as read: {e}',
            'error_details': str(e)
        }


# ===========================================
# Server Entry Point
# ===========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Email MCP Server')
    parser.add_argument('--transport', default='stdio', choices=['stdio', 'http'],
                        help='Transport protocol (default: stdio)')
    parser.add_argument('--port', type=int, default=8801,
                        help='Port for HTTP transport (default: 8801)')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host for HTTP transport (default: 127.0.0.1)')
    parser.add_argument('--path', default='/mcp',
                        help='URL path for HTTP transport (default: /mcp)')

    args = parser.parse_args()

    if args.transport == 'http':
        print(f"Starting Email MCP Server with HTTP transport on {args.host}:{args.port}{args.path}")
        mcp.run(transport='http', host=args.host, port=args.port)
    else:
        print("Starting Email MCP Server with stdio transport")
        mcp.run()