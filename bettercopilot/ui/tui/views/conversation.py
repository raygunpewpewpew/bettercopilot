"""TUI view: conversation (console fallback)."""
from typing import List, Dict, Optional


def show(log: Optional[List[Dict]] = None):
    print('\n--- Conversation ---')
    if not log:
        print('(no conversation yet)')
        return
    for item in log[-10:]:
        role = item.get('role', 'assistant')
        content = item.get('content') or item.get('text') or ''
        print(f"[{role}] {content[:200]}")
