"""Detect project type based on files present in a workspace.

Supports detection of ROM hacking, Python projects, and assembly projects.
"""
import os
from typing import Optional


def detect_project_type(path: str = ".") -> Optional[str]:
    try:
        files = os.listdir(path)
    except Exception:
        return None

    lower = [f.lower() for f in files]
    # ROM detection
    if any(f.endswith('.gba') or f.endswith('.bin') or f.endswith('.ips') for f in lower):
        return 'rom'

    # Assembly detection
    if any(f.endswith('.s') or f.endswith('.asm') or f.endswith('.thumb') or f.endswith('.inc') for f in lower):
        return 'assembly'

    # Python detection
    if any(f.endswith('.py') for f in files):
        return 'python'

    return None
