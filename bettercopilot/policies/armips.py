"""Very small Armips policy checks.

Armips is an assembly preprocessor/assembler used by ROM hackers. These
checks are intentionally lightweight.
"""
from typing import List, Dict


def validate(code: str) -> List[Dict]:
    diagnostics = []
    lines = code.splitlines()
    for i, l in enumerate(lines, start=1):
        if l.strip().startswith("##"):
            diagnostics.append({"policy": "armips", "message": "Commented macro? check syntax", "line": i, "severity": "info"})
    return diagnostics
