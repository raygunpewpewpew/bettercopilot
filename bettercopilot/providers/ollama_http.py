"""Ollama HTTP provider integration.

This provider calls a local Ollama HTTP server (default http://localhost:11434)
and normalizes responses into the provider interface used by BetterCopilot.

It supports both the `/api/generate` and `/api/chat` endpoints and will
attempt a few retries on transient errors. If `requests` isn't installed,
the provider returns an error shape instead of raising.
"""
from typing import Any, Dict, List, Optional
import os
import time
import logging

try:
    import requests
except Exception:
    requests = None

from .base import Provider


class OllamaHTTPProvider(Provider):
    def __init__(self, api_url: Optional[str] = None, model: Optional[str] = None, logger: Optional[logging.Logger] = None):
        super().__init__(name='ollama', logger=logger)
        self.api_url = (api_url or os.getenv('OLLAMA_URL') or os.getenv('OLLAMA_HOST') or 'http://localhost:11434').rstrip('/')
        self.model = model or os.getenv('OLLAMA_MODEL', 'qwen2.5-coder')
        self._no_requests = requests is None
        if not self._no_requests:
            self.session = requests.Session()

    def _post(self, path: str, payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        if self._no_requests:
            return {'error': 'requests_missing', 'payload': payload}

        url = f"{self.api_url}/{path.lstrip('/')}"
        attempts = 0
        while attempts < 3:
            attempts += 1
            try:
                resp = self.session.post(url, json=payload, timeout=timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                try:
                    if self.logger:
                        self.logger.exception('Ollama request failed (attempt %d): %s', attempts, e)
                except Exception:
                    pass
                time.sleep(0.35 * attempts)

        return {'error': 'ollama_request_failed'}

    def generate(self, messages: Optional[List[Dict[str, Any]]] = None, tools: Optional[List[Dict]] = None, system: Optional[str] = None, suffix: Optional[str] = None, options: Optional[Dict] = None) -> Dict[str, Any]:
        """Call Ollama and return a normalized dict with `text`, `tool_calls`, `raw`."""
        payload: Dict[str, Any] = {'model': self.model}
        if options:
            payload['options'] = options

        # Decide whether this looks like a chat-style interaction
        is_chat = bool(messages and any(isinstance(m, dict) and 'role' in m for m in messages))

        # Build candidate endpoint paths to try (some Ollama servers expose different paths)
        if is_chat:
            candidate_paths = [
                '/api/chat', '/chat', '/v1/chat', '/api/chat/completions', '/chat/completions', '/v1/chat/completions',
                '/api/conversations', '/conversations', '/completions', '/api/completions', '/v1/completions'
            ]
        else:
            candidate_paths = [
                '/api/generate', '/generate', '/v1/generate', '/api/completions', '/completions', '/v1/completions'
            ]

        # Prepare payload for the variant
        if is_chat:
            payload['messages'] = messages
        else:
            # Build a prompt string from messages if needed, otherwise empty
            prompt = ''
            if messages:
                if isinstance(messages, list):
                    prompt = '\n'.join([m.get('content') if isinstance(m, dict) else str(m) for m in messages])
                else:
                    prompt = str(messages)
            payload['prompt'] = prompt
            if suffix is not None:
                payload['suffix'] = suffix

        data = None
        last_error = None
        tried = []
        for path in candidate_paths:
            try:
                tried.append(path)
                d = self._post(path, payload)
            except Exception as e:
                last_error = e
                d = {'error': str(e)}

            # Heuristic: consider successful if response is dict and contains expected keys
            if isinstance(d, dict) and not d.get('error'):
                # common success indicators
                if any(k in d for k in ('text', 'choices', 'output', 'generation', 'generations', 'result', 'content')):
                    data = d
                    break
                # some servers return nested structures
                if isinstance(d.get('choices'), list) and len(d.get('choices')) > 0:
                    data = d
                    break

            # otherwise keep trying next endpoint
            last_error = d

        if data is None:
            # fallback to last response or an error marker
            if last_error is None:
                data = {'error': 'ollama_request_failed', 'tried': tried}
            else:
                data = last_error if isinstance(last_error, dict) else {'error': str(last_error), 'tried': tried}

        # Normalize text out of common Ollama response shapes
        text = ''
        tool_calls = []
        if isinstance(data, dict):
            # direct text
            if isinstance(data.get('text'), str) and data.get('text'):
                text = data.get('text')
            # OpenAI-like choices
            elif isinstance(data.get('choices'), list) and len(data.get('choices')) > 0:
                first = data.get('choices')[0]
                if isinstance(first, dict):
                    # some servers nest message/content
                    msg = first.get('message') or {}
                    if isinstance(msg, dict) and msg.get('content'):
                        text = msg.get('content')
                    else:
                        text = first.get('text') or ''
                else:
                    text = str(first)
            # direct output
            elif isinstance(data.get('output'), str) and data.get('output'):
                text = data.get('output')
            # generation shapes
            elif isinstance(data.get('generation'), dict):
                text = data.get('generation').get('text') or ''
            elif isinstance(data.get('generations'), list) and len(data.get('generations')) > 0:
                g = data.get('generations')[0]
                if isinstance(g, dict):
                    text = g.get('text') or ''

            tool_calls = data.get('tool_calls') or []
        else:
            text = str(data)

        return {'text': text, 'tool_calls': tool_calls, 'raw': data}
