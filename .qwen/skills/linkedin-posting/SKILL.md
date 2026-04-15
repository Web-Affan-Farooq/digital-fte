---
name: linkedin-posting
description: |
  Post content to LinkedIn using browser automation (Playwright). Supports creating
  posts, draft posts for approval, and profile info retrieval. Use when tasks require
  social media posting, business updates, or professional content sharing.
---

# LinkedIn Posting Skill

Post to LinkedIn via Playwright-based MCP server built with FastMCP.

## MCP Server Setup

### Start LinkedIn MCP Server

```bash
# Start with stdio transport (for Claude Code integration)
uv run python mcp-servers/linkedin/server.py

# Or start with HTTP transport
uv run python mcp-servers/linkedin/server.py --transport http --port 8802
```

### Configure Claude Code MCP

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uv",
      "args": ["run", "python", "mcp-servers/linkedin/server.py"]
    }
  }
}
```

### LinkedIn Credentials

Set environment variables:

```bash
export LINKEDIN_EMAIL=your.email@example.com
export LINKEDIN_PASSWORD=your_password
export PLAYWRIGHT_HEADLESS=true  # Set to 'false' for visible browser
```

**Note:** For security, use a credential manager instead of plain text passwords.

## Tools

### create_post

Create and publish a post on LinkedIn.

```bash
uv run python scripts/mcp-client.py call -t create_post -p '{
  "content": "Excited to announce our new product launch! #innovation #startup",
  "hashtags": ["innovation", "startup", "tech"]
}'
```

**Parameters:**
- `content` (required): Post content text
- `image_path` (optional): Path to image to attach
- `hashtags` (optional): List of hashtags to append

### create_draft_post

Create a draft post for approval (does not publish).

```bash
uv run python scripts/mcp-client.py call -t create_draft_post -p '{
  "content": "Our Q1 results are in and we exceeded all targets!",
  "hashtags": ["business", "growth", "success"]
}'
```

This creates a draft file in `/Pending_Approval/` for human review.

### get_profile_info

Get current LinkedIn profile information.

```bash
uv run python scripts/mcp-client.py call -t get_profile_info -p '{}'
```

### close_session

Close LinkedIn browser session.

```bash
uv run python scripts/mcp-client.py call -t close_session -p '{}'
```

## Workflow: Post Business Update

1. Generate post content based on business goals
2. Create draft post (creates file in `/Pending_Approval/`)
3. Human reviews and moves file to `/Approved/`
4. Orchestrator detects approval and publishes post

## Workflow: Automated Sales Post

1. Read Business_Goals.md for messaging
2. Generate post about services/products
3. Create draft with hashtags
4. Await approval
5. On approval, publish via MCP server

## Environment Variables

```bash
# LinkedIn credentials
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_password

# Browser settings
PLAYWRIGHT_HEADLESS=true

# Vault path
VAULT_PATH=./vault

# Dry run mode
DRY_RUN=true  # Set to 'false' for production
```

## Approval Workflow

Draft posts are saved to `/Pending_Approval/`:

```markdown
---
type: linkedin_post_draft
created: 2026-01-07T10:30:00Z
status: pending_approval
content_length: 150
hashtags: ["business", "growth"]
---

# LinkedIn Post Draft

## Content

Our Q1 results are in and we exceeded all targets!

---

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Not logged in | Check credentials, scan QR if needed |
| Post not publishing | Check DRY_RUN variable |
| Browser not starting | Install Playwright: `uv run playwright install chromium` |
| Session expired | Close session and re-authenticate |

## Related Skills

- [email-sending](../email-sending/) - Email communication
- [whatsapp-monitoring](../whatsapp-monitoring/) - WhatsApp monitoring
