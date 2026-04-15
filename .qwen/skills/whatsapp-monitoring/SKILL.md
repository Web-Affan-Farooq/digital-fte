---
name: whatsapp-monitoring
description: |
  Monitor WhatsApp Web for new messages using Playwright browser automation.
  Detects messages containing keywords (urgent, invoice, payment, etc.) and
  creates action files in the Obsidian vault. Use when tasks require monitoring
  WhatsApp for business inquiries, urgent messages, or client communication.
---

# WhatsApp Monitoring Skill

Monitor WhatsApp Web for messages using Playwright-based watcher.

## Setup

### Install Dependencies

```bash
uv sync
uv run playwright install chromium
```

### Configure Environment

```bash
# WhatsApp session storage
export WHATSAPP_SESSION_PATH=~/.digital_fte/sessions/whatsapp

# Vault path
export VAULT_PATH=./vault

# Check interval (seconds)
export CHECK_INTERVAL=30

# Keywords to monitor
export WHATSAPP_KEYWORDS=urgent,asap,invoice,payment,help,important

# Dry run mode
export DRY_RUN=true
```

## Usage

### Start WhatsApp Watcher

```bash
# Start monitoring
uv run python scripts/whatsapp_watcher.py --vault ./vault

# With custom keywords
uv run python scripts/whatsapp_watcher.py --keywords "urgent,payment,client"

# With custom interval
uv run python scripts/whatsapp_watcher.py --interval 60
```

### First Run - QR Code Login

1. Start the watcher
2. WhatsApp Web will load in browser
3. Scan QR code with your phone
4. Session is saved for future runs

## How It Works

1. **Browser Launch**: Opens Chromium with persistent session
2. **WhatsApp Web**: Navigates to web.whatsapp.com
3. **Message Scanning**: Checks unread chats for keywords
4. **Action File Creation**: Creates `.md` file in `/Needs_Action/`
5. **Processing**: Claude Code processes action files

## Action File Format

When a message matches keywords:

```markdown
---
type: whatsapp_message
chat_name: John Doe
received: 2026-01-07T10:30:00Z
priority: high
status: pending
matched_keywords: ["urgent", "invoice"]
message_id: John_Doe_20260107_1030
---

# WhatsApp Message

## From
**John Doe**

## Received
2026-01-07 10:30:00

## Priority
HIGH

## Matched Keywords
urgent, invoice

---

## Message Content

Hey, can you send me the invoice urgently?

---

## Suggested Actions

- [ ] Read and understand the message
- [ ] Draft reply (requires approval before sending)
- [ ] Take necessary action based on request
- [ ] Mark as processed
```

## Keyword Detection

Default keywords:
- `urgent` - High priority
- `asap` - High priority
- `invoice` - Business related
- `payment` - Financial
- `help` - Support request
- `important` - High priority

Customize via `WHATSAPP_KEYWORDS` environment variable.

## Integration with Orchestrator

```bash
# Start all watchers including WhatsApp
uv run python scripts/orchestrator.py start --watchers filesystem whatsapp

# Process detected messages
uv run python scripts/orchestrator.py process

# Ralph loop for autonomous processing
uv run python scripts/orchestrator.py ralph-loop "Process all WhatsApp messages"
```

## Reply Workflow

1. WhatsApp message detected → Action file in `/Needs_Action/`
2. Claude Code processes → Draft reply created
3. Approval file in `/Pending_Approval/`
4. Human approves → Moves to `/Approved/`
5. Reply sent via WhatsApp MCP (future) or manual

## Environment Variables

```bash
# Session storage
WHATSAPP_SESSION_PATH=~/.digital_fte/sessions/whatsapp

# Monitoring
CHECK_INTERVAL=30  # Seconds between checks
WHATSAPP_KEYWORDS=urgent,asap,invoice,payment,help

# Browser
PLAYWRIGHT_HEADLESS=true

# Vault
VAULT_PATH=./vault

# Dry run
DRY_RUN=true
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| QR code not showing | Clear session folder and restart |
| No messages detected | Check if WhatsApp Web is loaded |
| Browser crashes | Set `PLAYWRIGHT_HEADLESS=false` to debug |
| Session expired | Re-scan QR code |

## Security Notes

- Session data stored locally in `~/.digital_fte/sessions/whatsapp`
- Never commit session files to version control
- Use dedicated business WhatsApp account for automation
- Be aware of WhatsApp's terms of service

## Related Skills

- [email-sending](../email-sending/) - Email communication
- [linkedin-posting](../linkedin-posting/) - Social media posting
