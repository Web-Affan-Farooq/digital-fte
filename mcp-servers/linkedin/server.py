"""
LinkedIn MCP Server for Digital FTE

Provides LinkedIn posting capabilities via browser automation (Playwright).
Built using FastMCP framework.

Usage:
    # Start server with stdio transport (for Claude Code)
    uv run python mcp-servers/linkedin/server.py
    
    # Start server with HTTP transport
    uv run python mcp-servers/linkedin/server.py --transport http --port 8802

Environment Variables:
    LINKEDIN_EMAIL: LinkedIn account email
    LINKEDIN_PASSWORD: LinkedIn account password (use credential manager in production)
    LINKEDIN_SESSION_PATH: Path to persist browser session
    DRY_RUN: Set to 'true' to log posts without publishing
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastmcp import FastMCP
from config import dry_run

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not installed. Run: uv add playwright")


# ===========================================
# Server Configuration
# ===========================================

mcp = FastMCP(
    name="Digital FTE LinkedIn Server",
    # dependencies=["playwright"],
)

# Global browser state
_browser_context: Optional[BrowserContext] = None
_linkedin_logged_in = False


# ===========================================
# Browser Management
# ===========================================

def get_session_path() -> Path:
    """Get path to LinkedIn session storage."""
    home = Path.home()
    session_dir = home / '.digital_fte' / 'sessions' / 'linkedin'
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def get_browser_context() -> Optional[BrowserContext]:
    """Get or create persistent browser context."""
    global _browser_context
    
    if _browser_context is not None:
        return _browser_context
    
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available")
        return None
    
    try:
        playwright = sync_playwright().start()
        
        session_path = get_session_path()
        
        # Launch persistent context
        _browser_context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(session_path),
            headless=os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        
        return _browser_context
        
    except Exception as e:
        print(f"Failed to create browser context: {e}")
        return None


def close_browser():
    """Close browser context."""
    global _browser_context, _linkedin_logged_in
    
    if _browser_context:
        try:
            _browser_context.close()
        except Exception:
            pass
        _browser_context = None
    _linkedin_logged_in = False


def ensure_logged_in(context: BrowserContext) -> bool:
    """
    Ensure LinkedIn is logged in.
    
    Returns:
        True if logged in successfully
    """
    global _linkedin_logged_in
    
    if _linkedin_logged_in:
        return True
    
    page = context.pages[0] if context.pages else context.new_page()
    
    # Check if already logged in
    page.goto('https://www.linkedin.com/feed/')
    page.wait_for_load_state('networkidle')
    
    # Check if we're on feed page (logged in)
    if 'feed' in page.url:
        _linkedin_logged_in = True
        return True
    
    # Need to login
    email = os.getenv('LINKEDIN_EMAIL')
    password = os.getenv('LINKEDIN_PASSWORD')
    
    if not email or not password:
        print("LinkedIn credentials not set. Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD")
        return False
    
    # Go to login page
    page.goto('https://www.linkedin.com/login')
    page.wait_for_load_state('networkidle')
    
    try:
        # Fill credentials
        email_input = page.locator('input[id="username"]')
        if email_input.is_visible():
            email_input.fill(email)
        
        password_input = page.locator('input[id="password"]')
        if password_input.is_visible():
            password_input.fill(password)
        
        # Click sign in
        sign_in_btn = page.locator('button[type="submit"]')
        if sign_in_btn.is_visible():
            sign_in_btn.click()
        
        # Wait for navigation
        page.wait_for_load_state('networkidle')
        time.sleep(3)  # Wait for redirect
        
        # Check if login successful
        if 'feed' in page.url or 'mynetwork' in page.url:
            _linkedin_logged_in = True
            print("LinkedIn login successful")
            return True
        else:
            print("LinkedIn login may have failed. Current URL:", page.url)
            return False
            
    except Exception as e:
        print(f"Login error: {e}")
        return False


# ===========================================
# MCP Tools
# ===========================================

@mcp.tool()
def create_post(
    content: str,
    image_path: Optional[str] = None,
    hashtags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a post on LinkedIn.
    
    Args:
        content: Post content text
        image_path: Optional path to image to attach
        hashtags: Optional list of hashtags to append
    
    Returns:
        Dictionary with status and post details
    """    
    # Append hashtags
    if hashtags:
        hashtag_text = ' '.join(f'#{tag}' for tag in hashtags)
        content = f"{content}\n\n{hashtag_text}"
    
    if dry_run:
        return {
            'status': 'dry_run',
            'message': 'Post not published (DRY_RUN mode)',
            'details': {
                'content': content[:200] + '...' if len(content) > 200 else content,
                'image': image_path,
                'hashtags': hashtags
            }
        }
    
    if not PLAYWRIGHT_AVAILABLE:
        return {
            'status': 'error',
            'message': 'Playwright not installed'
        }
    
    context = get_browser_context()
    if not context:
        return {
            'status': 'error',
            'message': 'Failed to create browser context'
        }
    
    if not ensure_logged_in(context):
        return {
            'status': 'error',
            'message': 'Not logged in to LinkedIn'
        }
    
    try:
        page = context.pages[0] if context.pages else context.new_page()
        
        # Go to LinkedIn feed
        page.goto('https://www.linkedin.com/feed/')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Click on "Start a post"
        start_post = page.locator('button:has-text("Start a post")').first
        if start_post.is_visible():
            start_post.click()
            time.sleep(1)
        else:
            # Try alternative selector
            post_area = page.locator('[aria-label="Start a post"]').first
            if post_area.is_visible():
                post_area.click()
                time.sleep(1)
        
        # Find and fill the text area
        text_area = page.locator('div[contenteditable="true"][role="textbox"]').first
        if text_area.is_visible():
            text_area.fill(content)
            time.sleep(1)
        else:
            return {
                'status': 'error',
                'message': 'Could not find post text area'
            }
        
        # Handle image upload if provided
        if image_path:
            try:
                # Click media button
                media_btn = page.locator('button[aria-label*="Media"], button[aria-label*="Photo"], button[aria-label*="Image"]').first
                if media_btn.is_visible():
                    media_btn.click()
                    time.sleep(1)
                    
                    # Upload file
                    file_input = page.locator('input[type="file"]').first
                    file_input.set_input_files(image_path)
                    time.sleep(2)
            except Exception as e:
                print(f"Image upload warning: {e}")
        
        # Click Post button
        post_btn = page.locator('button:has-text("Post")').last
        if post_btn.is_visible():
            post_btn.click()
            time.sleep(3)
            
            # Check if post was successful
            if 'posted' in page.content().lower() or page.url == 'https://www.linkedin.com/feed/':
                return {
                    'status': 'success',
                    'message': 'Post published successfully',
                    'content_preview': content[:100] + '...' if len(content) > 100 else content
                }
        
        return {
            'status': 'warning',
            'message': 'Post action completed but could not verify',
            'content_preview': content[:100] + '...' if len(content) > 100 else content
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to create post: {e}',
            'error_details': str(e)
        }


@mcp.tool()
def create_draft_post(
    content: str,
    hashtags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a draft post for LinkedIn (does not publish).
    Prepares the content and saves to vault for approval.
    
    Args:
        content: Post content text
        hashtags: Optional list of hashtags to append
    
    Returns:
        Dictionary with draft details and file path
    """
    # Append hashtags
    if hashtags:
        hashtag_text = ' '.join(f'#{tag}' for tag in hashtags)
        content = f"{content}\n\n{hashtag_text}"
    
    # Create draft file in vault
    vault_path = Path(os.getenv('VAULT_PATH', './vault'))
    drafts_folder = vault_path / 'Pending_Approval'
    drafts_folder.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    draft_file = drafts_folder / f'LINKEDIN_POST_{timestamp}.md'
    
    draft_content = f"""---
type: linkedin_post_draft
created: {datetime.now().isoformat()}
status: pending_approval
content_length: {len(content)}
hashtags: {hashtags or []}
---

# LinkedIn Post Draft

## Content

{content}

---

## To Approve
1. Review the content above
2. Move this file to /Approved folder
3. The post will be published automatically

## To Reject
Move this file to /Rejected folder or delete.

---

## Publishing Instructions
Run: `uv run python mcp-servers/linkedin/server.py --publish <draft_id>`
Or use the orchestrator to process approved drafts.
"""
    
    draft_file.write_text(draft_content, encoding='utf-8')
    
    return {
        'status': 'draft_created',
        'draft_file': str(draft_file),
        'content_preview': content[:100] + '...' if len(content) > 100 else content,
        'action': 'move_to_approved_to_publish'
    }


@mcp.tool()
def get_profile_info() -> Dict[str, Any]:
    """
    Get current LinkedIn profile information.
    
    Returns:
        Dictionary with profile details
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {
            'status': 'error',
            'message': 'Playwright not installed'
        }
    
    context = get_browser_context()
    if not context:
        return {
            'status': 'error',
            'message': 'Failed to create browser context'
        }
    
    if not ensure_logged_in(context):
        return {
            'status': 'error',
            'message': 'Not logged in to LinkedIn'
        }
    
    try:
        page = context.pages[0] if context.pages else context.new_page()
        
        # Go to profile page
        page.goto('https://www.linkedin.com/in/me/')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Extract basic info
        name = ''
        headline = ''
        
        try:
            name_el = page.locator('h1').first
            if name_el.is_visible():
                name = name_el.inner_text()
        except Exception:
            pass
        
        try:
            headline_el = page.locator('div:text-has-text("at")').first
            if headline_el.is_visible():
                headline = headline_el.inner_text()
        except Exception:
            pass
        
        return {
            'status': 'success',
            'name': name,
            'headline': headline,
            'url': page.url
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to get profile: {e}',
            'error_details': str(e)
        }


@mcp.tool()
def close_session() -> Dict[str, Any]:
    """
    Close LinkedIn browser session.
    
    Returns:
        Dictionary with status
    """
    close_browser()
    return {
        'status': 'success',
        'message': 'LinkedIn session closed'
    }


# ===========================================
# Server Entry Point
# ===========================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='LinkedIn MCP Server')
    parser.add_argument('--transport', default='stdio', choices=['stdio', 'http'])
    parser.add_argument('--port', type=int, default=8802)
    parser.add_argument('--host', default='127.0.0.1')
    
    args = parser.parse_args()
    
    if args.transport == 'http':
        mcp.run(transport='http', host=args.host, port=args.port)
    else:
        mcp.run()
