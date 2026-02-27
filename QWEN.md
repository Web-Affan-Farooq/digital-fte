# Digital FTE - Project Context

## Project Overview

**Digital FTE** (Full-Time Equivalent) is a personal AI employee system that autonomously manages personal and business affairs 24/7. It uses **Claude Code** as the reasoning engine and **Obsidian** as the knowledge dashboard, with lightweight Python "Watcher" scripts monitoring inputs (Gmail, WhatsApp, filesystems) and **MCP (Model Context Protocol)** servers handling external actions.

**Tagline:** *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DIGITAL FTE ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PERCEPTION (Watchers) → REASONING (Claude) → ACTION (MCP) │
│                                                             │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │ Gmail Watcher│    │             │    │ Email MCP    │   │
│  │ WhatsApp     │───▶│ QWEN code   │───▶│ Browser MCP  │   │
│  │ File Watcher │    │ (Brain)     │    │ Payment MCP  │   │
│  └──────────────┘    └─────────────┘    └──────────────┘   │
│         │                   │                    │          │
│         ▼                   ▼                    ▼          │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │ /Needs_Action│    │ Plan.md     │    │ Human-in-    │   │
│  │ /Inbox       │    │ Dashboard.md│    │ the-Loop     │   │
│  └──────────────┘    └─────────────┘    └──────────────┘   │
│                                                             │
│              Obsidian Vault (Memory/GUI)                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Watchers** | Python scripts monitoring Gmail, WhatsApp, filesystems | Planned: `/watchers/` |
| **Claude Code** | Reasoning engine with Ralph Wiggum persistence loop | External tool |
| **Obsidian Vault** | Dashboard.md, Company_Handbook.md, task folders | Local Markdown |
| **MCP Servers** | External action handlers (email, browser, payments) | Configured via `mcp.json` |
| **Skills** | Agent skills for Claude Code | `.agents/skills/` |

## Repository Structure

```
G:\digital-fte\
├── README.md                    # Project description
├── doc.md                       # Comprehensive architectural blueprint
├── skills-lock.json             # Skills version tracking
├── QWEN.md                      # This file - AI context
└── .agents/
    └── skills/
        └── browsing-with-playwright/
            ├── SKILL.md         # Browser automation skill
            ├── references/
            │   └── playwright-tools.md  # MCP tool schemas
            └── scripts/
                ├── mcp-client.py        # Universal MCP client
                ├── start-server.sh      # Start Playwright MCP
                ├── stop-server.sh       # Stop Playwright MCP
                └── verify.py            # Server health check
```

## Building and Running

### Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| [Claude Code](https://claude.com/product/claude-code) | Latest | Reasoning engine |
| [Obsidian](https://obsidian.md/download) | v1.10.6+ | Knowledge dashboard |
| [Python](https://www.python.org/downloads/) | 3.13+ | Watcher scripts |
| [Node.js](https://nodejs.org/) | v24+ LTS | MCP servers |
| [GitHub Desktop](https://desktop.github.com/download/) | Latest | Version control |

### Playwright MCP Setup

```bash
# Start the Playwright MCP server
bash .agents/skills/browsing-with-playwright/scripts/start-server.sh

# Verify server is running
python .agents/skills/browsing-with-playwright/scripts/verify.py

# Stop the server when done
bash .agents/skills/browsing-with-playwright/scripts/stop-server.sh
```

### MCP Client Usage

```bash
# List available tools
python scripts/mcp-client.py list --url http://localhost:8808

# Call a tool
python scripts/mcp-client.py call -u http://localhost:8808 -t browser_navigate \
  -p '{"url": "https://example.com"}'

# Emit tool schemas as markdown
python scripts/mcp-client.py emit --url http://localhost:8808
```

### Ralph Wiggum Persistence Loop

The "Ralph Wiggum" pattern keeps Claude working until tasks are complete:

```bash
# Start a Ralph loop
/ralph-loop "Process all files in /Needs_Action, move to /Done when complete" \
  --completion-promise "TASK_COMPLETE" \
  --max-iterations 10
```

## Development Conventions

### Folder Structure (Obsidian Vault)

```
Vault/
├── Inbox/                 # Raw incoming items
├── Needs_Action/          # Items requiring processing
├── In_Progress/<agent>/   # Claimed tasks (claim-by-move rule)
├── Pending_Approval/      # Human-in-the-loop approvals
├── Approved/              # User-approved actions
├── Done/                  # Completed tasks
├── Plans/                 # Generated plan files
├── Briefings/             # CEO briefing reports
├── Accounting/            # Transaction logs
└── Dashboard.md           # Real-time status summary
```

### Human-in-the-Loop Pattern

For sensitive actions, Claude writes an approval request file:

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

### Security Rules

- **Secrets never sync**: `.env`, tokens, WhatsApp sessions, banking credentials stay local
- **Single-writer rule**: Only Local writes to `Dashboard.md`
- **Claim-by-move**: First agent to move item to `/In_Progress/<agent>/` owns it

## Hackathon Tiers

| Tier | Description | Estimated Time |
|------|-------------|----------------|
| **Bronze** | Foundation: Obsidian vault, one watcher, basic Claude integration | 8-12 hours |
| **Silver** | Functional: Multiple watchers, MCP servers, HITL workflow | 20-30 hours |
| **Gold** | Autonomous: Full integration, Odoo accounting, Ralph loop | 40+ hours |
| **Platinum** | Production: Cloud deployment, delegation, 24/7 operation | 60+ hours |

## Key Features

### Monday Morning CEO Briefing

Autonomous weekly audit generating:
- **Revenue**: Total earned this week
- **Bottlenecks**: Tasks that took too long
- **Proactive Suggestions**: Cost optimization, subscription audits

### Watcher Pattern

All watchers follow this structure:

```python
from base_watcher import BaseWatcher

class MyWatcher(BaseWatcher):
    def check_for_updates(self) -> list:
        """Return list of new items to process"""
        pass

    def create_action_file(self, item) -> Path:
        """Create .md file in Needs_Action folder"""
        pass
```
## Related Documentation

- [`doc.md`](doc.md) - Full architectural blueprint and hackathon guide
- [`README.md`](README.md) - Project summary
- [`.agents/skills/browsing-with-playwright/SKILL.md`](.agents/skills/browsing-with-playwright/SKILL.md) - Browser automation skill
