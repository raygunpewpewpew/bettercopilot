"""Refinement engine: applies patches, auto-fixes, or requests retries.

This module applies trivial automatic fixes (via the policy engine) or
constructs instructions that the orchestrator can use to retry generation.
"""
from typing import Any, Dict


class RefinementEngine:
    def __init__(self, policy_engine):
        self.policy_engine = policy_engine

    def refine(self, original_output: Dict[str, Any], diagnostics: list) -> Dict[str, Any]:
        text = original_output.get('text', '')
        # Try auto-fix
        fixed = self.policy_engine.auto_fix(diagnostics, text)
        changed = fixed != text
        return {"changed": changed, "fixed_text": fixed, "request_retry": not changed and len(diagnostics) > 0}
