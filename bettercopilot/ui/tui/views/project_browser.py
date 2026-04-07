"""TUI view: project browser (simple console output)."""
from typing import Optional


def show(context: Optional[dict] = None):
    print('\n--- Project Browser ---')
    if not context:
        print('(no context available)')
        return
    print(f"Project type: {context.get('project_type')}")
    files = context.get('selected_files') or []
    print(f"{len(files)} selected files:")
    for f in files[:20]:
        print(' -', f)
