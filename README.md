# Digital FTE - Personal AI Employee

> **Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.**

Digital FTE (Full-Time Equivalent) is a personal AI employee system that autonomously manages personal and business affairs 24/7. It uses **qwen code cli** as the reasoning engine and **Obsidian** as the knowledge dashboard, with lightweight Python "Watcher" scripts monitoring inputs (Gmail, WhatsApp, filesystems).

## 🏆 Hackathon Status: Bronze Tier

This repository implements the **Bronze Tier** foundation:

- ✅ Obsidian vault with Dashboard.md and Company_Handbook.md
- ✅ One working Watcher script (filesystem monitoring)
- ✅ qwen code cli integration for reading/writing to vault
- ✅ Basic folder structure: /Inbox, /Needs_Action, /Done
- ✅ Gmail watcher (requires API setup)
- ✅ Orchestrator with Ralph Wiggum loop

## 📋 Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| [qwen code cli](https://qwen code.com/product/qwen code-code) | Latest | Reasoning engine |
| [Obsidian](https://obsidian.md/download) | v1.10.6+ | Knowledge dashboard |
| [Python](https://www.python.org/downloads/) | 3.13+ | Watcher scripts |
| [Node.js](https://nodejs.org/) | v24+ LTS | MCP servers (future) |
| [GitHub Desktop](https://desktop.github.com/download/) | Latest | Version control |

## 🚀 Quick Start

### 1. Clone the Repository

```bash
cd G:\digital-fte
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

```bash
# Copy the example environment file
copy .env.example .env

# Edit .env with your settings
```

### 4. Open Vault in Obsidian

```
File → Open Vault → Select G:\digital-fte\vault
```

### 5. Test the System

```bash
# Check system status
uv run scripts/orchestrator.py status

# Start filesystem watcher (dry run)
uv run scripts/filesystem_watcher.py --vault ./vault

# Process with qwen code cli
uv run scripts/orchestrator.py process
```

## 📁 Project Structure

```
G:\digital-fte\
├── README.md                 # This file
├── doc.md                    # Full architectural blueprint
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── scripts/
│   ├── base_watcher.py       # Base class for all watchers
│   ├── gmail_watcher.py      # Gmail monitoring
│   ├── filesystem_watcher.py # File drop monitoring
│   └── orchestrator.py       # Main coordinator + Ralph loop
└── vault/                    # Obsidian vault
    ├── Dashboard.md          # Real-time status
    ├── Company_Handbook.md   # Rules of engagement
    ├── Business_Goals.md     # Objectives & metrics
    ├── Inbox/                # Raw incoming items
    ├── Needs_Action/         # Items requiring processing
    ├── In_Progress/          # Claimed tasks
    ├── Pending_Approval/     # Human-in-the-loop approvals
    ├── Approved/             # User-approved actions
    ├── Done/                 # Completed tasks
    ├── Plans/                # Generated plans
    ├── Briefings/            # CEO briefing reports
    ├── Accounting/           # Transaction logs
    └── Logs/                 # System logs
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Vault Configuration
VAULT_PATH=./vault

# Dry Run Mode (set to 'false' for production)
DRY_RUN=true

# Gmail Watcher (optional)
GMAIL_CREDENTIALS_PATH=~/.gmail_watcher/credentials.json
GMAIL_TOKEN_PATH=~/.gmail_watcher/token.json

# Filesystem Watcher
DROP_FOLDER_PATH=./vault/Inbox/Drop
CHECK_INTERVAL=30

# Ralph Loop
MAX_ITERATIONS=10
```

### Gmail API Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download `credentials.json`
6. Place in `~/.gmail_watcher/credentials.json`
7. Run authentication:

```bash
uv run scripts/gmail_watcher.py --auth --vault ./vault
```

## 📖 Usage

### Start Watchers

```bash
# Activate venv 
.venv/Scripts/activate
```

```bash
# Start all watchers
uv run scripts/orchestrator.py start

# Start specific watcher
uv run scripts/filesystem_watcher.py --vault ./vault

# Gmail watcher (if configured)
uv run scripts/gmail_watcher.py --vault ./vault
```

### Process with qwen code cli

```bash
# Process Needs_Action folder
uv run scripts/orchestrator.py process

# Custom prompt
uv run scripts/orchestrator.py process --prompt "Review all pending approvals"

# Ralph Wiggum loop (autonomous multi-step)
uv run scripts/orchestrator.py ralph-loop "Process all files in /Needs_Action"
```

### Check Status

```bash
uv run scripts/orchestrator.py status
```

## 🤖 How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DIGITAL FTE ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────┤
│  PERCEPTION (Watchers) → REASONING (qwen code) → ACTION (MCP) │
│                                                             │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │ Gmail Watcher│    │             │    │ (Future:     │   │
│  │ File Watcher │───▶│ qwen code cli │───▶│  Email MCP)  │   │
│  └──────────────┘    │ (Brain)     │    └──────────────┘   │
│                      └─────────────┘                       │
│                            │                                │
│                            ▼                                │
│                      ┌─────────────┐                        │
│                      │ Obsidian    │                        │
│                      │ Vault       │                        │
│                      └─────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Workflow

1. **Watcher detects input** (new email, file drop, etc.)
2. **Creates action file** in `/Needs_Action/` folder
3. **Orchestrator triggers qwen code cli** to process
4. **qwen code reads** Company_Handbook.md for rules
5. **qwen code creates plan** in `/Plans/` folder
6. **qwen code requests approval** for sensitive actions
7. **Human reviews** and moves files to `/Approved/`
8. **Action executed** (future: via MCP servers)
9. **Files moved to `/Done/`** and Dashboard updated

### Human-in-the-Loop Pattern

For sensitive actions, qwen code creates approval requests:

```markdown
---
type: approval_request
action: payment
amount: 500.00
recipient: Client A
status: pending
---

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
```

## 🎯 Bronze Tier Checklist

- [x] Obsidian vault with proper folder structure
- [x] Dashboard.md tracking key metrics
- [x] Company Handbook defining rules
- [x] At least one watcher script operational (filesystem)
- [x] Gmail watcher implemented (requires API setup)
- [x] qwen code cli successfully processing files
- [x] Orchestrator with Ralph Wiggum loop
- [ ] Test with real files and qwen code cli

## 📈 Next Steps (Silver Tier)

1. Set up Gmail API credentials
2. Implement MCP server for email sending
3. Add WhatsApp watcher (Playwright-based)
4. Create automated plan generation
5. Set up scheduled operations via Task Scheduler

## 🔐 Security

- **Secrets never sync**: `.env`, tokens, credentials stay local
- **Dry run mode**: Test without real actions
- **Approval workflow**: Sensitive actions require human approval
- **Audit logging**: All actions logged to `/Logs/`

## 🐛 Troubleshooting

### qwen code cli not found

```bash
npm install -g @anthropic/qwen code-code
```

### Gmail API error

- Ensure credentials.json is in correct location
- Run `uv run scripts/gmail_watcher.py --auth` to re-authenticate

### Watcher not detecting files

- Check `DROP_FOLDER_PATH` environment variable
- Ensure folder exists and has read permissions
- Check logs in `/vault/Logs/`

## 📚 Documentation

- [doc.md](doc.md) - Full architectural blueprint
- [vault/Company_Handbook.md](vault/Company_Handbook.md) - Rules of engagement
- [vault/Business_Goals.md](vault/Business_Goals.md) - Objectives and metrics
- [vault/Dashboard.md](vault/Dashboard.md) - Real-time status

## 🤝 Contributing

This is a hackathon project. Feel free to:
- Fork and extend functionality
- Add new watchers
- Implement MCP servers
- Improve documentation

## 📄 License

MIT License - See LICENSE file for details

## 🎓 Learning Resources

- [qwen code cli Chapter](https://agentfactory.panaversity.org/docs/AI-Tool-Landscape/qwen code-code-features-and-workflows)
- [Obsidian Fundamentals](https://help.obsidian.md/Getting+started)
- [MCP Introduction](https://modelcontextprotocol.io/introduction)
- [Agent Skills](https://platform.qwen code.com/docs/en/agents-and-tools/agent-skills/overview)

---

*Built with ❤️ for the Digital FTE Hackathon 2026*

**Version:** 0.1 (Bronze Tier) | **Last Updated:** 2026-01-07