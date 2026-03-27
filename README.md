# Digital FTE - Personal AI Employee (Silver Tier)

> **Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.**

Digital FTE (Full-Time Equivalent) is a personal AI employee system that autonomously manages personal and business affairs 24/7. It uses **Qwen Code** as the reasoning engine and **Obsidian** as the knowledge dashboard, with lightweight Python "Watcher" scripts monitoring inputs (Gmail, WhatsApp, filesystems) and **FastMCP** servers handling external actions.

## 🏆 Hackathon Status: Silver Tier

This repository implements the **Silver Tier** with all Bronze features plus:

### ✅ Silver Tier Deliverables

- [x] All Bronze requirements (vault, watchers, Qwen integration)
- [x] **Two or more Watcher scripts** (Gmail + WhatsApp + Filesystem)
- [x] **Automatically Post on LinkedIn** (via MCP server with approval workflow)
- [x] **Qwen reasoning loop** that creates Plan.md files
- [x] **Working MCP servers** built using FastMCP (Email + LinkedIn)
- [x] **Human-in-the-loop approval workflow** for sensitive actions
- [x] **Basic scheduling** via Task Scheduler integration
- [x] **All AI functionality as Agent Skills**

---

## 📋 Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| [Qwen Code](https://Qwen.com/product/Qwen-code) | Latest | Reasoning engine |
| [Obsidian](https://obsidian.md/download) | v1.10.6+ | Knowledge dashboard |
| [Python](https://www.python.org/downloads/) | 3.13+ | Watcher scripts & MCP servers |
| [UV](https://github.com/astral-sh/uv) | Latest | Python package manager |
| [Node.js](https://nodejs.org/) | v24+ LTS | MCP servers (optional) |

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd G:\digital-fte

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Sync UV environment
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### 2. Configure Environment

```bash
# Copy environment template
copy .env.example .env

# Edit .env with your settings
# IMPORTANT: Set DRY_RUN=false for production use
```

### 3. Setup Gmail API (Optional)

```bash
# Download credentials.json from Google Cloud Console
# Place in ~/.gmail_watcher/credentials.json

# First run will auto-authenticate
uv run python -m GmailWatcher.main --vault ./vault
```

### 4. Open Vault in Obsidian

```
File → Open Vault → Select G:\digital-fte\vault
```

### 5. Start Silver Tier

```bash
# Activate virtual environment
.venv\Scripts\activate

# Check system status
uv run python -m Orchestrator.main status

# Start all watchers
uv run python -m Orchestrator.main start

# Process files with Qwen (interactive mode - requires approval)
uv run python -m Orchestrator.main process

# Process files with Qwen (autonomous mode - auto-approves actions)
uv run python -m Orchestrator.main process --yolo
```

---

## 📁 Project Structure

```
G:\digital-fte\
├── README.md                     # This file
├── doc.md                        # Full architectural blueprint
├── pyproject.toml                # UV project configuration
├── .env.example                  # Environment variables template
├── .agents/
│   └── skills/
│       └── fastmcp/
│           └── templates/        # FastMCP server templates
├── mcp-servers/
│   ├── email/
│   │   └── server.py             # Email MCP server (FastMCP)
│   └── linkedin/
│       └── server.py             # LinkedIn MCP server (FastMCP)
├── scripts/
│   ├── base_watcher.py           # Base class for all watchers
│   ├── gmail_watcher.py          # Gmail monitoring
│   ├── filesystem_watcher.py     # File drop monitoring
│   ├── WhatsappWatcher           # WhatsApp Web monitoring
│   ├── orchestrator.py           # Main coordinator + Ralph loop
│   └── mcp-client.py             # MCP client helper
└── vault/                        # Obsidian vault
    ├── Dashboard.md              # Real-time status
    ├── Company_Handbook.md       # Rules of engagement
    ├── Business_Goals.md         # Objectives & metrics
    ├── Inbox/
    │   └── Drop/                 # Drop files here for processing
    ├── Needs_Action/             # Items requiring processing
    ├── In_Progress/              # Claimed tasks
    ├── Pending_Approval/         # Human-in-the-loop approvals
    ├── Approved/                 # User-approved actions
    ├── Done/                     # Completed tasks
    ├── Plans/                    # Generated plans
    ├── Briefings/                # CEO briefing reports
    ├── Accounting/               # Transaction logs
    └── Logs/                     # System logs
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# ===========================================
# VAULT CONFIGURATION
# ===========================================
VAULT_PATH=./vault

# ===========================================
# OPERATION MODE
# ===========================================

# Dry Run Mode: Set to 'true' to test without real actions
# Set to 'false' for production use
DRY_RUN=false

# ===========================================
# GMAIL WATCHER (Optional)
# ===========================================

# Path to Gmail OAuth credentials (downloaded from Google Cloud Console)
# Get credentials from: https://developers.google.com/gmail/api/quickstart/python
GMAIL_CREDENTIALS_PATH=~/.gmail_watcher/credentials.json

# Path to Gmail OAuth token (auto-generated after first auth)
GMAIL_TOKEN_PATH=~/.gmail_watcher/token.json

# ===========================================
# WHATSAPP WATCHER
# ===========================================
WHATSAPP_SESSION_PATH=~/.digital_fte/sessions/whatsapp
CHECK_INTERVAL=30
WHATSAPP_KEYWORDS=urgent,asap,invoice,payment,help

# ===========================================
# LINKEDIN POSTING
# ===========================================
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_password
PLAYWRIGHT_HEADLESS=true

# ===========================================
# ORCHESTRATOR
# ===========================================
MAX_ITERATIONS=10
```

---

## 📖 Usage

### Start Watchers

```bash
# Activate virtual environment first
.venv\Scripts\activate

# Start all watchers (runs in background)
uv run python -m Orchestrator.main start

# Start specific watchers
uv run python -m Orchestrator.main start --watchers filesystem whatsapp

# Start Gmail watcher (if configured)
uv run python -m GmailWatcher.main --vault ./vault

# Start filesystem watcher (monitors vault/Inbox/Drop)
uv run python -m FilesystemWatcher.main --vault ./vault

```

### Start MCP Servers

```bash
# Start Email MCP server (stdio transport for Qwen Code)
uv run python mcp-servers/email/server.py

# Start LinkedIn MCP server (stdio transport for Qwen Code)
uv run python mcp-servers/linkedin/server.py

# Or with HTTP transport (for external access)
uv run python mcp-servers/email/server.py --transport http --port 8801
uv run python mcp-servers/linkedin/server.py --transport http --port 8802
```

### Process with Qwen Code

```bash
# Interactive mode (requires approval for each action)
uv run python -m Orchestrator.main process

# Custom prompt
uv run python -m Orchestrator.main process --prompt "Review all pending approvals"


# Autonomous mode (YOLO - auto-approves all actions)
uv run python -m Orchestrator.main process --yolo


# Ralph Wiggum loop (autonomous multi-step processing)
uv run python -m Orchestrator.main ralph "Process all files in /Needs_Action"

```

### Process Approved Actions

```bash
# Execute all approved actions (emails, LinkedIn posts)
uv run python -m Orchestrator.main process-approvals

```

### Check Status

```bash
uv run python -m Orchestrator.main status

```

---

## 🤖 How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIGITAL FTE - SILVER TIER                    │
├─────────────────────────────────────────────────────────────────┤
│  PERCEPTION (Watchers) → REASONING (Qwen) → ACTION (MCP)     │
│                                                                 │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐       │
│  │ Gmail Watcher│    │             │    │ Email MCP    │       │
│  │ WhatsApp     │───▶│ Qwen Code │───▶│ LinkedIn MCP │       │
│  │ File Watcher │    │ (Brain)     │    │ (FastMCP)    │       │
│  └──────────────┘    └─────────────┘    └──────────────┘       │
│         │                   │                    │              │
│         ▼                   ▼                    ▼              │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐       │
│  │ /Needs_Action│    │ Plan.md     │    │ Human-in-    │       │
│  │ /Inbox       │    │ Dashboard.md│    │ the-Loop     │       │
│  └──────────────┘    └─────────────┘    └──────────────┘       │
│                                                                 │
│              Obsidian Vault (Memory/GUI)                        │
└─────────────────────────────────────────────────────────────────┘
```

### Workflow

1. **Watcher detects input** (new email, WhatsApp message, file drop)
2. **Creates action file** in `/Needs_Action/` folder
3. **Orchestrator triggers Qwen Code** to process
4. **Qwen reads** Company_Handbook.md for rules
5. **Qwen creates plan** in `/Plans/` folder
6. **Qwen requests approval** for sensitive actions (email, LinkedIn)
7. **Human reviews** and moves files to `/Approved/`
8. **MCP server executes** action (send email, post LinkedIn)
9. **Files moved to `/Done/`** and Dashboard updated

---

## 🛠️ MCP Servers

### Email MCP Server

Built with FastMCP, provides:
- `send_email` - Send emails via Gmail
- `draft_email` - Create draft emails
- `search_emails` - Search Gmail
- `get_email_content` - Get full email content
- `mark_as_read` - Mark emails as read

**Start:**
```bash
uv run python mcp-servers/email/server.py
```

### LinkedIn MCP Server

Built with FastMCP + Playwright, provides:
- `create_post` - Publish LinkedIn posts
- `create_draft_post` - Create draft for approval
- `get_profile_info` - Get profile information
- `close_session` - Close browser session

**Start:**
```bash
uv run python mcp-servers/linkedin/server.py
```

---

## ✅ Human-in-the-Loop Pattern

For sensitive actions, Qwen creates approval requests:

```markdown
---
type: approval_request
action: email_send
to: client@example.com
subject: Invoice #123
created: 2026-01-07T10:30:00Z
status: pending
---

## Email Details
- **To:** client@example.com
- **Subject:** Invoice #123
- **Body:** Please find attached...

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
```

**Approval Flow:**
1. File created in `/Pending_Approval/`
2. Human reviews content
3. **Move to `/Approved/`** to execute (or `/Rejected/` to cancel)
4. Orchestrator detects and calls MCP server
5. Action executed, file moved to `/Done/`

**One-line approval:** Move the approval request file from `/Pending_Approval/` to `/Approved/` folder.

---

## 🎯 Silver Tier Checklist

- [x] Obsidian vault with proper folder structure
- [x] Dashboard.md tracking key metrics
- [x] Company Handbook defining rules
- [x] Multiple watchers operational (Gmail + WhatsApp + Filesystem)
- [x] Qwen Code successfully processing files
- [x] MCP servers built with FastMCP (Email + LinkedIn)
- [x] Human-in-the-loop workflow complete
- [x] Approval execution via MCP servers
- [x] Agent Skills documented

---

## 📈 Next Steps (Gold Tier)

1. **Odoo Accounting Integration** - Self-hosted ERP via MCP
2. **Facebook/Instagram Integration** - Social media posting
3. **Twitter (X) Integration** - Tweet automation
4. **Weekly CEO Briefing** - Autonomous business audit
5. **Error Recovery** - Graceful degradation
6. **Comprehensive Audit Logging** - Full action history

---

## 🔐 Security

- **Secrets never sync**: `.env`, tokens, credentials stay local
- **Dry run mode**: Test without real actions
- **Approval workflow**: Sensitive actions require human approval
- **Audit logging**: All actions logged to `/Logs/`
- **Credential management**: Use OS keychain for passwords

---

## 🐛 Troubleshooting

### Qwen Code not found

```bash
npm install -g @anthropic/qwen-code

# Verify installation
qwen --version
```

### Qwen Code requires approval for every action

**Problem:** Qwen asks for approval before executing tools (write_file, run_shell_command, etc.)

**Solution 1 - Use YOLO mode (full autonomy):**
```bash
uv run python -m Orchestrator.main process --yolo

```

**Solution 2 - Run interactively:**
```bash
# Qwen will wait for your approval in the terminal
uv run python -m Orchestrator.main process 
```

### Gmail API error

- Ensure credentials.json is in `~/.gmail_watcher/`
- First run will auto-authenticate and create token.json
- Check Google Cloud Console has Gmail API enabled

### WhatsApp watcher not detecting messages

- Check if QR code was scanned on WhatsApp Web
- Verify `WHATSAPP_SESSION_PATH` exists
- Set `PLAYWRIGHT_HEADLESS=false` to debug visually

### MCP server not connecting

- Check server is running: `uv run python mcp-servers/email/server.py`
- Verify port is not in use
- Check firewall settings
- For Qwen Code integration, use stdio transport (default)

### Files not being processed from Drop folder

- Ensure filesystem watcher is running
- Check file isn't already processed (hash is tracked)
- Verify DRY_RUN=false in .env for actual processing

---

## 📚 Documentation

- [doc.md](doc.md) - Full architectural blueprint
- [vault/Company_Handbook.md](vault/Company_Handbook.md) - Rules of engagement
- [vault/Business_Goals.md](vault/Business_Goals.md) - Objectives and metrics
- [vault/Dashboard.md](vault/Dashboard.md) - Real-time status

---

## 🤝 Contributing

This is a hackathon project. Feel free to:
- Fork and extend functionality
- Add new watchers
- Implement additional MCP servers
- Improve documentation

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🎓 Learning Resources

- [Qwen Code Chapter](https://agentfactory.panaversity.org/docs/AI-Tool-Landscape/Qwen-code-features-and-workflows)
- [FastMCP Documentation](https://github.com/prefecthq/fastmcp)
- [Obsidian Fundamentals](https://help.obsidian.md/Getting+started)
- [MCP Introduction](https://modelcontextprotocol.io/introduction)
- [Agent Skills](https://platform.Qwen.com/docs/en/agents-and-tools/agent-skills/overview)

---

*Built with ❤️ for the Digital FTE Hackathon 2026*

**Version:** 0.2 (Silver Tier) | **Last Updated:** 2026-03-20
