"""Critic evaluates generated outputs against policies and other heuristics.

The critic produces structured feedback across categories and a composite
score in [0,1]. It also recommends whether the orchestrator should retry.
"""
from typing import Any, Dict, List
import re


class Critic:
    def __init__(self, policy_engine):
        self.policy_engine = policy_engine

    def _policy_score(self, diagnostics: List[Dict]) -> float:
        if not diagnostics:
            return 1.0
        # Map severities to a numeric penalty
        total = 0.0
        for d in diagnostics:
            sev = d.get('severity', 'info')
            if sev == 'error':
                total += 0.0
            elif sev == 'warning' or sev == 'warn':
                total += 0.5
            else:
                total += 0.9
        return max(0.0, min(1.0, total / len(diagnostics)))

    def _clarity_score(self, text: str) -> float:
        if not text:
            return 0.0
        # Heuristic: very long lines reduce clarity
        lines = text.splitlines()
        avg_len = sum(len(l) for l in lines) / max(1, len(lines))
        if avg_len < 80:
            return 1.0
        if avg_len < 200:
            return 0.8
        return 0.5

    def _safety_score(self, text: str) -> float:
        if not text:
            return 0.0
        unsafe_tokens = [r"\bkill\b", r"\bexplosive\b", r"\bweapon\b"]
        for tok in unsafe_tokens:
            if re.search(tok, text, flags=re.IGNORECASE):
                return 0.0
        return 1.0

    def _correctness_score(self, text: str) -> float:
        # Best-effort heuristic: presence of common markers like 'ERROR' reduces score
        if not text:
            return 0.0
        if 'error' in text.lower() or 'traceback' in text.lower():
            return 0.2
        return 1.0

    def _tool_usage_score(self, output: Dict[str, Any]) -> float:
        tool_calls = output.get('tool_calls') or []
        if not tool_calls:
            return 0.0
        return 1.0

    def evaluate(self, output: Dict[str, Any], policy_names: List[str]) -> Dict[str, Any]:
        text = output.get('text', '')
        diagnostics = self.policy_engine.run(policy_names, text)

        policy_score = self._policy_score(diagnostics)
        clarity = self._clarity_score(text)
        safety = self._safety_score(text)
        correctness = self._correctness_score(text)
        tool_usage = self._tool_usage_score(output)

        # Composite score (weighted)
        weights = {
            'correctness': 0.3,
            'policy_compliance': 0.25,
            'clarity': 0.15,
            'safety': 0.2,
            'tool_usage': 0.1,
        }
        score = (
            correctness * weights['correctness']
            + policy_score * weights['policy_compliance']
            + clarity * weights['clarity']
            + safety * weights['safety']
            + tool_usage * weights['tool_usage']
        )

        # Retry heuristics
        recommend_retry = False
        if score < 0.75:
            recommend_retry = True
        if any(d.get('severity') == 'error' for d in diagnostics):
            recommend_retry = True
        if tool_usage == 0.0 and 'inspect' in text.lower():
            # heuristics: if user asked for inspection but tools not used
            recommend_retry = True

        return {
            'score': max(0.0, min(1.0, score)),
            'categories': {
                'correctness': correctness,
                'policy_compliance': policy_score,
                'clarity': clarity,
                'safety': safety,
                'tool_usage': tool_usage,
            },
            'diagnostics': diagnostics,
            'recommend_retry': recommend_retry,
        }
