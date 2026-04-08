"""Perplexity free provider (simulated).

Unified provider shape and simple retry behaviour.
"""
from .base import Provider
from typing import Any, Dict, List, Optional
import time


class PerplexityFreeProvider(Provider):
    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, system: Optional[str] = None, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        self.logger.info("PerplexityFreeProvider.generate called; messages=%d", len(messages))
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
                time.sleep(0.01)
                reply = f"[Perplexity simulated response] {content}"
                try:
                    if callable(progress_callback) and isinstance(reply, str) and reply:
                        words = reply.split()
                        total_parts = min(4, max(1, len(words) // 50 + 1))
                        part_size = max(1, len(words) // total_parts)
                        assembled = ''
                        parts = []
                        for i in range(0, len(words), part_size):
                            parts.append(' '.join(words[i:i+part_size]))
                        total = len(parts) if parts else 1
                        for idx, part in enumerate(parts):
                            assembled = (assembled + ' ' + part).strip() if assembled else part
                            try:
                                progress_callback('provider_stream', {'provider': self.name, 'partial': assembled, 'index': idx, 'total': total})
                            except Exception:
                                pass
                            try:
                                time.sleep(0.01)
                            except Exception:
                                pass
                except Exception:
                    pass

                return {"text": reply, "tool_calls": tool_calls, "raw": {"provider": "perplexity_free"}}
            except Exception as e:
                self.logger.exception("Perplexity provider error on attempt %d: %s", attempts, e)
                time.sleep(0.02 * attempts)

        return {"text": "", "tool_calls": tool_calls, "raw": {"error": "failed_to_generate"}}
