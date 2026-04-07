"""Simple GBA THUMB policy validator.

This module contains a few deterministic checks useful for ensuring generated
assembly follows expected rules for GBA THUMB code.
"""
import re
from typing import List, Dict


def validate(code: str) -> List[Dict]:
    """Return a list of diagnostics for the given assembly `code`.

    Diagnostics are dicts with keys: policy, message, line, severity.
    """
    diagnostics = []
    lines = code.splitlines()
    # Check for .thumb directive
    if not any(re.match(r"\s*\.thumb", l) for l in lines[:5]):
        diagnostics.append({"policy": "gba_thumb", "message": "Missing .thumb directive near top of file", "line": 1, "severity": "warning"})

    # Disallow tabs (force spaces)
    for i, l in enumerate(lines, start=1):
        if "\t" in l:
            diagnostics.append({"policy": "gba_thumb", "message": "Tab character found; use spaces for indentation", "line": i, "severity": "info"})

    return diagnostics
