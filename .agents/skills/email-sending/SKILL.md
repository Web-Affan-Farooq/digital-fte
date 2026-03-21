---
name: email-sending
description: |
  Send emails via Gmail using the Email MCP server. Supports sending, drafting,
  searching emails, and marking as read. Use when tasks require email communication,
  sending invoices, replying to clients, or managing Gmail inbox.
---

# Email Sending Skill

Send and manage emails via Gmail MCP server built with FastMCP.

## MCP Server Setup

### Start Email MCP Server

```bash
# Start with stdio transport (for Claude Code integration)
uv run python mcp-servers/email/server.py

# Or start with HTTP transport
uv run python mcp-servers/email/server.py --transport http --port 8801
```

### Configure Claude Code MCP

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "email": {
      "command": "uv",
      "args": ["run", "python", "mcp-servers/email/server.py"]
    }
  }
}
```

### Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download `credentials.json`
6. Place in `~/.gmail_watcher/credentials.json`
7. First run will auto-generate token

## Tools

### send_email

Send an email via Gmail.

```bash
uv run python scripts/mcp-client.py call -t send_email -p '{
  "to": "client@example.com",
  "subject": "Invoice #123",
  "body": "Please find attached your invoice...",
  "html": false
}'
```

**Parameters:**
- `to` (required): Recipient email address
- `subject` (required): Email subject
- `body` (required): Email body content
- `from_email` (optional): Sender email
- `cc` (optional): CC recipients (comma-separated)
- `bcc` (optional): BCC recipients (comma-separated)
- `html` (optional): Whether body is HTML (default: false)

### draft_email

Create a draft email in Gmail (does not send).

```bash
uv run python scripts/mcp-client.py call -t draft_email -p '{
  "to": "client@example.com",
  "subject": "Proposal for Project",
  "body": "Dear Client, Here is the proposal..."
}'
```

### search_emails

Search emails in Gmail.

```bash
# Find unread emails
uv run python scripts/mcp-client.py call -t search_emails -p '{
  "query": "is:unread",
  "max_results": 10
}'

# Find emails from specific sender
uv run python scripts/mcp-client.py call -t search_emails -p '{
  "query": "from:client@example.com",
  "max_results": 5
}'
```

**Parameters:**
- `query` (required): Gmail search query
- `max_results` (optional): Maximum results (default: 10)

### get_email_content

Get full content of a specific email.

```bash
uv run python scripts/mcp-client.py call -t get_email_content -p '{
  "message_id": "123abc"
}'
```

### mark_as_read

Mark an email as read.

```bash
uv run python scripts/mcp-client.py call -t mark_as_read -p '{
  "message_id": "123abc"
}'
```

## Workflow: Reply to Client Email

1. Search for unread emails
2. Get email content
3. Draft reply (requires approval)
4. On approval, send email

## Workflow: Send Invoice

1. Create invoice PDF
2. Draft email with attachment
3. Create approval file in `/Pending_Approval/`
4. On approval (file moved to `/Approved/`), send email

## Environment Variables

```bash
# Gmail credentials
GMAIL_CREDENTIALS_PATH=~/.gmail_watcher/credentials.json
GMAIL_TOKEN_PATH=~/.gmail_watcher/token.json

# Dry run mode
DRY_RUN=true  # Set to 'false' for production
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Authentication failed | Re-run server to trigger OAuth flow |
| Credentials not found | Download from Google Cloud Console |
| Email not sending | Check DRY_RUN environment variable |
| API quota exceeded | Wait and retry, or increase quota |

## Related Skills

- [linkedin-posting](../linkedin-posting/) - Social media posting
- [whatsapp-monitoring](../whatsapp-monitoring/) - WhatsApp message monitoring
