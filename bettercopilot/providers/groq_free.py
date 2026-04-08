"""Groq free-tier provider (simulated).

Implements the provider interface and returns structured dicts. Simulated
behaviour includes a small retry policy and basic tool-call suggestion when
the message asks for a lookup (prefix "lookup:").
"""
from .base import Provider
from typing import Any, Dict, List, Optional
import time
import requests
from ..config import get_provider_config


class GroqFreeProvider(Provider):
    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, system: Optional[str] = None, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        self.logger.info("GroqFreeProvider.generate called; messages=%d", len(messages))
        attempts = 0
        last_user = None
        for m in reversed(messages or []):
            if m.get('role') == 'user':
                last_user = m
                break

        content = (last_user or {}).get('content', '')
        tool_calls: List[Dict] = []

        # If user asked for a lookup in the form "lookup:topic", propose a tool call
        if isinstance(content, str) and 'lookup:' in content.lower():
            try:
                topic = content.split(':', 1)[1].strip()
            except Exception:
                topic = content
            tool_calls.append({"tool": "deepwiki", "method": "query", "params": {"q": topic}})

        # If a real Groq config is present, attempt real HTTP call (best-effort)
        cfg = get_provider_config('groq')
        if cfg.get('api_key') and cfg.get('base_url'):
            url = cfg.get('base_url')
            headers = {'Authorization': f"Bearer {cfg.get('api_key')}"}
            payload = {"messages": messages, "model": cfg.get('model'), "temperature": cfg.get('temperature', 0.0)}
            backoff = 0.1
            while attempts < cfg.get('max_retries', 3):
                attempts += 1
                try:
                    resp = requests.post(url, json=payload, headers=headers, timeout=5)
                    resp.raise_for_status()
                    data = resp.json()
                    # Map to standard shape
                    text = data.get('text') or data.get('result') or ''
                    # Emit provider_stream with the returned text if a callback was provided
                    try:
                        if callable(progress_callback) and isinstance(text, str) and text:
                            words = text.split()
                            total_parts = min(6, max(1, len(words) // 60 + 1))
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
                                    time.sleep(0.02)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    return {"text": text, "tool_calls": tool_calls, "raw": data}
                except Exception as e:
                    self.logger.exception("Groq HTTP error on attempt %d: %s", attempts, e)
                    time.sleep(backoff)
                    backoff *= 2

        while attempts < 3:
            attempts += 1
            try:
                time.sleep(0.02)
                text = f"[GroqFree simulated response] {content}"
                try:
                    if callable(progress_callback) and isinstance(text, str) and text:
                        words = text.split()
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

                return {"text": text, "tool_calls": tool_calls, "raw": {"provider": "groq_free", "messages": messages}}
            except Exception as e:
                self.logger.exception("Groq provider error on attempt %d: %s", attempts, e)
                time.sleep(0.05 * attempts)

        return {"text": "", "tool_calls": tool_calls, "raw": {"error": "failed_to_generate"}}
