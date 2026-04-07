"""Ollama local provider integration (simulated local model runner).

Local provider wrapper that follows the unified provider interface.
"""
from .base import Provider
from typing import Any, Dict, List, Optional
import time


class OllamaLocalProvider(Provider):
    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, system: Optional[str] = None) -> Dict[str, Any]:
        self.logger.info("OllamaLocalProvider.generate called; messages=%d", len(messages))
        attempts = 0
        last_user = None
        for m in reversed(messages or []):
            if m.get('role') == 'user':
                last_user = m
                break

        content = (last_user or {}).get('content', '')
        tool_calls: List[Dict] = []

        if isinstance(content, str) and content.lower().startswith('lookup:'):
            topic = content.split(':', 1)[1].strip()
            tool_calls.append({"tool": "deepwiki", "method": "query", "params": {"q": topic}})

        while attempts < 3:
            attempts += 1
            try:
                # Simulate local computation
                time.sleep(0.01)
                return {"text": f"[OllamaLocal simulated] {content}", "tool_calls": tool_calls, "raw": {"provider": "ollama_local"}}
            except Exception as e:
                self.logger.exception("OllamaLocal error on attempt %d: %s", attempts, e)
                time.sleep(0.01 * attempts)

        return {"text": "", "tool_calls": tool_calls, "raw": {"error": "failed_to_generate"}}
