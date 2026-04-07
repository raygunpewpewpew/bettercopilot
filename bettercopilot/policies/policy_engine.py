"""Policy engine that runs deterministic checks and optionally applies fixes.

The engine exposes a simple API for running policies and producing diagnostics.
This is intentionally small so it can be embedded into the meta-critic loop.
"""
from typing import List, Dict, Callable, Optional
from . import python_style, gba_thumb, armips


class PolicyEngine:
    def __init__(self):
        # Register available policies
        self._policies = {
            "python_style": python_style.validate,
            "gba_thumb": gba_thumb.validate,
            "armips": armips.validate,
        }
        # Bundles group policies for convenience
        self._bundles = {
            "gba_rom_hacking": ["gba_thumb", "armips"],
            "python": ["python_style"],
            "assembly": ["armips"],
        }

    def list_policies(self) -> List[str]:
        return list(self._policies.keys())

    def run(self, policy_names: List[str], code: str) -> List[Dict]:
        diagnostics = []
        for name in policy_names:
            fn = self._policies.get(name)
            if fn:
                diagnostics.extend(fn(code))
        return diagnostics

    def auto_fix(self, diagnostics: List[Dict], code: str) -> str:
        # For this minimal engine, only a very small set of fixes are applied.
        lines = code.splitlines()
        changed = False
        new_lines = []
        for i, l in enumerate(lines, start=1):
            if any(d for d in diagnostics if d.get('line') == i and d.get('message') == 'Trailing whitespace'):
                changed = True
                new_lines.append(l.rstrip())
            else:
                new_lines.append(l)
        return "\n".join(new_lines) if changed else code

    def assess(self, code: str, policy_names: List[str]) -> Dict[str, object]:
        """Run policies, attempt auto-fixes, and return assessment.

        Returns a dict with keys:
          - diagnostics: list of diagnostics
          - corrected_code: code after auto-fix (may equal input)
          - acceptable: bool (no diagnostics with severity 'error')
        """
        diagnostics = self.run(policy_names, code)
        corrected = self.auto_fix(diagnostics, code)
        acceptable = not any(d.get('severity') == 'error' for d in diagnostics)
        return {"diagnostics": diagnostics, "corrected_code": corrected, "acceptable": acceptable}

    def resolve_bundle(self, name: str) -> List[str]:
        return self._bundles.get(name, [])

    def list_bundles(self) -> List[str]:
        return list(self._bundles.keys())
