import sys
from rich import print

def PrintStatus(self) -> None:
    """
    Print current system status to console.
    
    Args:
        self: Orchestrator instance
    """
    status = self.get_status()

    # Use ASCII-safe icons for Windows compatibility
    is_windows = sys.platform.startswith('win')
    if is_windows:
        icons = {
            'robot': '[FTE]',
            'vault': '[DIR]',
            'mode': '[MODE]',
            'time': '[TIME]',
            'chart': '[STATS]',
            'red': '[!]',
            'yellow': '[*]',
            'green': '[OK]',
            'server': '[MCP]',
            'watcher': '[W]'
        }
    else:
        icons = {
            'robot': '🤖',
            'vault': '📁',
            'mode': '🔧',
            'time': '⏰',
            'chart': '📊',
            'red': '🔴',
            'yellow': '🟡',
            'green': '🟢',
            'server': '🖥️',
            'watcher': '👁️'
        }

    print("\n" + "=" * 60)
    print(f"{icons['robot']} Digital FTE Status - Silver Tier")
    print("=" * 60)
    print(f"\n{icons['vault']} Vault: {status['vault_path']}")
    print(f"{icons['mode']} Mode: {'Dry Run' if status['dry_run'] else 'Production'}")
    print(f"{icons['time']} Updated: {status['timestamp']}")

    print(f"\n{icons['chart']} Folder Status:")
    for folder, count in status['folders'].items():
        icon = icons['red'] if count > 5 else icons['yellow'] if count > 0 else icons['green']
        print(f"  {icon} /{folder}: {count} files")

    print(f"\n{icons['watcher']} Watchers:")
    if status['watchers']:
        for watcher, state in status['watchers'].items():
            icon = icons['green'] if state == 'running' else icons['watcher']
            print(f"  {icon} {watcher}: {state}")
    else:
        print("  (none running)")

    print(f"\n{icons['server']} MCP Servers:")
    if status['mcp_servers']:
        for server, state in status['mcp_servers'].items():
            icon = icons['green'] if state == 'running' else icons['server']
            print(f"  {icon} {server}: {state}")
    else:
        print("  (none running)")

    print("\n" + "=" * 60 + "\n")
