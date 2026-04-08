"""OpenRouter provider integration.

This provider calls the OpenRouter chat completions API. It reads the
API key from the `OPENROUTER_API_KEY` environment variable by default
but accepts an explicit `api_key` parameter.

Do NOT store API keys in the repository. Set `OPENROUTER_API_KEY` in
your shell before launching the GUI, for example (Windows PowerShell):

  $env:OPENROUTER_API_KEY = 'sk-...'
  python scripts/run_gui_launcher.py

"""
from typing import Any, Dict, List, Optional
import os
import time
import logging
import requests

from .base import Provider


class OpenRouterProvider(Provider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None, logger: Optional[logging.Logger] = None):
        super().__init__(name='openrouter', logger=logger)
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv('OPENROUTER_MODEL', os.getenv('OPENROUTER_MODEL_NAME', 'gpt-4o-mini'))
        # Use the documented OpenRouter API host by default.
        self.base_url = base_url or os.getenv('OPENROUTER_API_BASE', 'https://openrouter.ai/api/v1')

        if not self.api_key:
            # Do not raise at import-time; only when instantiated for use.
            raise RuntimeError('OpenRouter API key not provided. Set OPENROUTER_API_KEY env var or pass api_key.')

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        })

    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, system: Optional[str] = None, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Call OpenRouter chat completions and return a normalized dict.

        Returns a dict containing at least `text` and `raw` fields and
        optionally `tool_calls`.
        """
        url = self.base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': self.model,
            'messages': messages,
        }

        attempts = 0
        while attempts < 3:
            attempts += 1
            try:
                resp = self.session.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                # Extract text from common OpenRouter/OpenAI-like shapes
                text = ''
                choices = data.get('choices') if isinstance(data, dict) else None
                if choices and len(choices) > 0:
                    ch = choices[0]
                    # Try nested message content
                    if isinstance(ch, dict):
                        message = ch.get('message') or {}
                        if isinstance(message, dict):
                            text = message.get('content') or message.get('text') or ch.get('text') or ''
                        else:
                            text = ch.get('text') or ''
                    else:
                        text = str(ch)
                else:
                    # fallback to other fields
                    if isinstance(data, dict) and 'output' in data:
                        out = data.get('output')
                        if isinstance(out, str):
                            text = out
                        elif isinstance(out, dict):
                            text = out.get('text') or ''

                # Emit a provider_stream event with incremental partials if requested.
                try:
                    if callable(progress_callback) and isinstance(text, str) and text:
                        # Chunk the final text into a few parts for a smooth UI stream
                        words = text.split()
                        total_parts = min(6, max(1, len(words) // 40 + 1))
                        part_size = max(1, len(words) // total_parts)
                        assembled = ''
                        parts = []
                        for i in range(0, len(words), part_size):
                            parts.append(' '.join(words[i:i+part_size]))
                        total = len(parts) if parts else 1
                        for idx, part in enumerate(parts):
                            if assembled:
                                assembled += ' ' + part
                            else:
                                assembled = part
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

                return {'text': text, 'tool_calls': data.get('tool_calls') or [], 'raw': data}

            except Exception as e:
                self.logger.exception('OpenRouter request failed (attempt %d): %s', attempts, e)
                time.sleep(0.5 * attempts)

        return {'text': '', 'tool_calls': [], 'raw': {'error': 'openrouter_failed'}}
