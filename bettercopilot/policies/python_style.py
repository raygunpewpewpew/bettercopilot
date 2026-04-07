"""Simple Python style and syntax checks.

Provides deterministic checks (syntax, simple style) that are safe to run
locally without external formatting tools.
"""
import ast
from typing import List, Dict


def validate(code: str) -> List[Dict]:
    diagnostics = []
    try:
        ast.parse(code)
    except SyntaxError as e:
        diagnostics.append({"policy": "python_style", "message": f"SyntaxError: {e.msg}", "line": e.lineno or 0, "severity": "error"})
        return diagnostics

    # Basic style: avoid trailing whitespace
    for i, line in enumerate(code.splitlines(), start=1):
        if line.rstrip() != line:
            diagnostics.append({"policy": "python_style", "message": "Trailing whitespace", "line": i, "severity": "info"})

    return diagnostics
