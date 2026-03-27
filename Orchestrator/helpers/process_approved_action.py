import re
from pathlib import Path
from typing import Dict

def ProcessApprovedAction(self, filepath: Path) -> bool:
    """
    Process an approved action file by calling the appropriate MCP server.
    
    Args:
        self: Orchestrator instance
        filepath: Path to approved action file
    
    Returns:
        True if processed successfully
    """
    try:
        content = filepath.read_text(encoding='utf-8')

        # Parse frontmatter
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            self.logger.warning(f"No frontmatter found in {filepath}")
            return False

        frontmatter = frontmatter_match.group(1)
        metadata = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        action_type = metadata.get('type', '')

        # Route to appropriate MCP server
        if 'email' in action_type.lower():
            return self._execute_email_action(filepath, metadata, content)
        elif 'linkedin' in action_type.lower():
            return self._execute_linkedin_action(filepath, metadata, content)
        else:
            self.logger.warning(f"Unknown action type: {action_type}")
            return False

    except Exception as e:
        self.logger.error(f"Error processing approved action: {e}")
        return False
