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
import json
from pathlib import Path

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
            # Attempt to discover available models and prefer a matching
            # model id (some Ollama installs include a version suffix in
            # the model id, e.g. `qwen2.5-coder:1.5b-base`). If the configured
            # `self.model` is a prefix, try to resolve to an exact available id.
            try:
                resp = None
                try:
                    resp = self.session.get(f"{self.api_url}/v1/models", timeout=1.0)
                except Exception:
                    # fall back to /v1/models without timeout or different path
                    try:
                        resp = self.session.get(f"{self.api_url}/models", timeout=1.0)
                    except Exception:
                        resp = None
                if resp is not None and getattr(resp, 'status_code', None) and resp.status_code < 400:
                    try:
                        j = resp.json()
                        models = j.get('data') if isinstance(j, dict) and 'data' in j else j
                        if isinstance(models, list):
                            for m in models:
                                mid = m.get('id') if isinstance(m, dict) else str(m)
                                if mid and isinstance(self.model, str) and mid.startswith(self.model):
                                    self.logger.info('Resolved Ollama model %s -> %s', self.model, mid)
                                    self.model = mid
                                    break
                    except Exception:
                        pass
            except Exception:
                pass

    def _post(self, path: str, payload: Dict[str, Any], timeout: float = 30.0, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        if self._no_requests:
            return {'error': 'requests_missing', 'payload': payload}

        url = f"{self.api_url}/{path.lstrip('/')}"

        def _append_debug_line(d: Dict[str, Any]):
            try:
                candidates = [Path.cwd()]
                try:
                    pkg_root = Path(__file__).resolve().parents[4]
                    candidates.append(pkg_root)
                except Exception:
                    pass
                candidates.append(Path.home())
                for base in candidates:
                    try:
                        logfile = Path(base) / 'debug_log.txt'
                        logfile.parent.mkdir(parents=True, exist_ok=True)
                        with open(logfile, 'a', encoding='utf-8') as f:
                            f.write(json.dumps(d, ensure_ascii=False) + '\n')
                        break
                    except Exception:
                        continue
            except Exception:
                pass
        attempts = 0
        last_error = None
        while attempts < 3:
            attempts += 1
            try:
                try:
                    _append_debug_line({'ts': time.time(), 'event': 'ollama_post_attempt', 'url': url, 'attempt': attempts, 'payload_preview': str(payload)[:200]})
                except Exception:
                    pass
                # Use streaming POST so we can handle chunked/JSONL responses
                resp = self.session.post(url, json=payload, timeout=timeout, stream=True)
                status = getattr(resp, 'status_code', None)
                try:
                    _append_debug_line({'ts': time.time(), 'event': 'ollama_post_response', 'url': url, 'status': status})
                except Exception:
                    pass

                # Try to read response incrementally to accommodate Ollama's
                # streaming JSON fragments. We'll collect lines and attempt
                # to parse them; if a progress callback is provided we will
                # also emit incremental `provider_stream` events as fragments
                # are parsed. Preserve assembled parts so we can return
                # them if the final body ends up empty.
                body = None
                lines = []
                assembled_parts = []
                idx = 0
                try:
                    # iter_lines yields bytes decoded to text when decode_unicode=True
                    for ln in resp.iter_lines(decode_unicode=True):
                        if ln is None:
                            continue
                        s = ln.strip()
                        if not s:
                            continue
                        lines.append(s)
                        parsed = None
                        try:
                            parsed = json.loads(s)
                        except Exception:
                            parsed = None

                        # Try to extract textual content from the fragment
                        fragment_content = None
                        try:
                            if isinstance(parsed, dict):
                                if isinstance(parsed.get('message'), dict):
                                    fragment_content = parsed['message'].get('content')
                                if not fragment_content and parsed.get('response'):
                                    fragment_content = parsed.get('response')
                                if not fragment_content and parsed.get('text'):
                                    fragment_content = parsed.get('text')
                                if not fragment_content and isinstance(parsed.get('choices'), list) and parsed['choices']:
                                    first = parsed['choices'][0]
                                    if isinstance(first, dict):
                                        msg = first.get('message') or {}
                                        fragment_content = msg.get('content') or first.get('text') or first.get('content')
                        except Exception:
                            fragment_content = None

                        if fragment_content:
                            assembled_parts.append(str(fragment_content))
                            partial = ''.join(assembled_parts).strip()
                            try:
                                if callable(progress_callback):
                                    progress_callback('provider_stream', {'provider': self.name, 'partial': partial, 'fragment': parsed, 'index': idx, 'total': None})
                            except Exception:
                                pass
                            idx += 1

                    # Attempt to interpret the collected lines as JSON if possible
                    if lines:
                        joined = '\n'.join(lines)
                        try:
                            body = json.loads(joined)
                        except Exception:
                            body = joined
                    else:
                        # No incremental lines; fall back to full-body parse
                        try:
                            body = resp.json()
                        except Exception:
                            try:
                                body = resp.text
                            except Exception:
                                body = None
                except Exception:
                    # Fall back to a simple parse on any streaming-read error
                    try:
                        body = resp.json()
                    except Exception:
                        try:
                            body = resp.text
                        except Exception:
                            body = None

                # If we collected streaming parts but the final parsed body
                # is empty or None, synthesize a body from the assembled parts
                try:
                    if (body is None or (isinstance(body, str) and not body.strip())) and assembled_parts:
                        joined_parts = ''.join(assembled_parts).strip()
                        if joined_parts:
                            # prefer returning a JSON-like dict so callers can
                            # treat it as a normal 'text' response
                            body = {'text': joined_parts}
                            # include assembled metadata so callers can inspect
                            try:
                                body['assembled_text'] = joined_parts
                                body['raw_stream_parts'] = list(assembled_parts)
                                body['streamed'] = True
                            except Exception:
                                pass
                except Exception:
                    pass

                # Emit a final provider_stream event with the assembled text
                try:
                    if assembled_parts and callable(progress_callback):
                        try:
                            final_text = ''.join(assembled_parts).strip()
                            progress_callback('provider_stream', {'provider': self.name, 'partial': final_text, 'final': True, 'fragment': None, 'index': max(0, idx-1) if isinstance(idx, int) else None, 'total': len(assembled_parts)})
                        except Exception:
                            pass
                except Exception:
                    pass

                # Success path
                if status is not None and 200 <= int(status) < 300:
                    try:
                        body_preview = None
                        try:
                            body_preview = str(body)
                        except Exception:
                            body_preview = repr(body)
                        _append_debug_line({'ts': time.time(), 'event': 'ollama_post_success', 'url': url, 'status': status, 'body_preview': body_preview[:2000] if body_preview else None})
                    except Exception:
                        pass
                    # Normalize and augment returned body
                    try:
                        if isinstance(body, dict) and assembled_parts:
                            try:
                                jp = ''.join(assembled_parts).strip()
                                if jp and not body.get('text'):
                                    body['text'] = jp
                                if 'assembled_text' not in body:
                                    body['assembled_text'] = jp
                                if 'raw_stream_parts' not in body:
                                    body['raw_stream_parts'] = list(assembled_parts)
                                body['streamed'] = True
                            except Exception:
                                pass
                    except Exception:
                        pass
                    return body if isinstance(body, dict) else ({'text': body} if body is not None else {'text': ''})

                # Non-2xx: keep structured error info for debugging and retry
                last_error = {'error': 'http_error', 'status_code': status, 'body': body, 'url': url}
                try:
                    _append_debug_line({'ts': time.time(), 'event': 'ollama_post_non2xx', 'url': url, 'status': status, 'body_preview': str(body)[:400], 'attempt': attempts})
                except Exception:
                    pass
                try:
                    if self.logger:
                        self.logger.warning('Ollama request returned status %s (attempt %d) for url: %s', status, attempts, url)
                except Exception:
                    pass
                time.sleep(0.35 * attempts)
            except Exception as e:
                last_error = {'error': 'exception', 'exception': str(e), 'url': url}
                try:
                    if self.logger:
                        self.logger.exception('Ollama request failed (attempt %d): %s', attempts, e)
                except Exception:
                    pass
                try:
                    _append_debug_line({'ts': time.time(), 'event': 'ollama_post_exception', 'url': url, 'exception': str(e), 'attempt': attempts})
                except Exception:
                    pass
                time.sleep(0.35 * attempts)

        # Exhausted retries; return last structured error
        return last_error or {'error': 'ollama_request_failed'}

    def is_available(self, timeout: float = 0.8) -> bool:
        """Lightweight probe for the Ollama HTTP server.

        Returns True if the base API URL responds to a simple GET within
        `timeout` seconds. This is intentionally lenient: any non-exception
        response suggests the server process is listening locally.
        """
        if self._no_requests:
            return False
        try:
            # Try a simple GET to the base URL — many Ollama installs respond
            # with a helpful HTML or JSON payload at the root. We accept any
            # non-exceptional response as availability.
            resp = self.session.get(self.api_url or '/', timeout=timeout)
            return resp is not None and resp.status_code < 500
        except Exception:
            return False

    def generate(self, messages: Optional[List[Dict[str, Any]]] = None, tools: Optional[List[Dict]] = None, system: Optional[str] = None, suffix: Optional[str] = None, options: Optional[Dict] = None, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Call Ollama and return a normalized dict with `text`, `tool_calls`, `raw`."""
        payload: Dict[str, Any] = {'model': self.model}
        if options:
            payload['options'] = options

        # Decide whether this looks like a chat-style interaction
        is_chat = bool(messages and any(isinstance(m, dict) and 'role' in m for m in messages))

        # Build candidate endpoint paths to try (some Ollama servers expose different paths)
        if is_chat:
            base_paths = [
                '/api/chat', '/chat', '/v1/chat', '/api/chat/completions', '/chat/completions', '/v1/chat/completions',
                '/api/conversations', '/conversations', '/completions', '/api/completions', '/v1/completions'
            ]
            # Also try model-specific variants
            model_paths = [
                f'/api/chat/{self.model}', f'/chat/{self.model}', f'/v1/chat/{self.model}',
                f'/api/chat/completions/{self.model}', f'/chat/completions/{self.model}', f'/v1/chat/completions/{self.model}',
                f'/api/conversations/{self.model}', f'/conversations/{self.model}'
            ]
            candidate_paths = base_paths + model_paths
        else:
            base_paths = [
                '/api/generate', '/generate', '/v1/generate', '/api/completions', '/completions', '/v1/completions'
            ]
            model_paths = [
                f'/api/generate/{self.model}', f'/generate/{self.model}', f'/v1/generate/{self.model}',
                f'/api/completions/{self.model}', f'/completions/{self.model}', f'/v1/completions/{self.model}',
                f'/models/{self.model}/generate', f'/v1/models/{self.model}/generate'
            ]
            candidate_paths = base_paths + model_paths

        # Prepare payload for the variant
        if is_chat:
            payload['messages'] = messages
            # Also include a simple `input` fallback built from message contents
            try:
                prompt = ''
                if messages and isinstance(messages, list):
                    prompt = '\n'.join([m.get('content') if isinstance(m, dict) else str(m) for m in messages])
                else:
                    prompt = str(messages or '')
                if prompt:
                    payload['input'] = prompt
            except Exception:
                pass
        else:
            # Build a prompt string from messages if needed, otherwise empty
            prompt = ''
            if messages:
                if isinstance(messages, list):
                    prompt = '\n'.join([m.get('content') if isinstance(m, dict) else str(m) for m in messages])
                else:
                    prompt = str(messages)
            # Use `input` which Ollama's HTTP API commonly expects for completions
            payload['input'] = prompt
            if suffix is not None:
                payload['suffix'] = suffix

        data = None
        last_error = None
        tried = []
        for path in candidate_paths:
            try:
                tried.append(path)
                d = self._post(path, payload, progress_callback=progress_callback)
                # If the server responded with a model-not-found error, try to
                # discover the exact model id and retry the same endpoint once.
                try:
                    if isinstance(d, dict) and d.get('error') and isinstance(d.get('body'), dict):
                        body = d.get('body')
                        if isinstance(body, dict) and isinstance(body.get('error'), str):
                            err_msg = body.get('error')
                            if 'not found' in err_msg and "model" in err_msg:
                                try:
                                    import re
                                    m = re.search(r"model\s+'([^']+)'\s+not found", err_msg)
                                    if m:
                                        missing = m.group(1)
                                        # query available models and try to resolve a matching id
                                        try:
                                            resp = None
                                            try:
                                                resp = self.session.get(f"{self.api_url}/v1/models", timeout=2.0)
                                            except Exception:
                                                try:
                                                    resp = self.session.get(f"{self.api_url}/models", timeout=2.0)
                                                except Exception:
                                                    resp = None
                                            if resp is not None and getattr(resp, 'status_code', None) and resp.status_code < 400:
                                                try:
                                                    j = resp.json()
                                                except Exception:
                                                    j = None
                                                models = j.get('data') if isinstance(j, dict) and 'data' in j else j
                                                if isinstance(models, list):
                                                    for mo in models:
                                                        mid = mo.get('id') if isinstance(mo, dict) else str(mo)
                                                        if mid and mid.startswith(missing):
                                                            # update configured model and retry
                                                            self.model = mid
                                                            try:
                                                                d_retry = self._post(path, payload, progress_callback=progress_callback)
                                                                d = d_retry
                                                            except Exception:
                                                                pass
                                                            break
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                except Exception:
                    pass
            except Exception as e:
                last_error = e
                d = {'error': str(e)}

            # Heuristic: consider successful if response is dict and contains expected keys
            if isinstance(d, dict) and not d.get('error'):
                # common success indicators (include Ollama-specific keys)
                if any(k in d for k in ('text', 'response', 'message', 'choices', 'output', 'generation', 'generations', 'result', 'content')):
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
        # If the selected endpoint returned a "loading" status (model still
        # warming up), retry the same endpoint a few times before giving up.
        try:
            def _is_loading_shape(d):
                if not isinstance(d, dict):
                    return False
                if d.get('done') is True and d.get('done_reason') == 'load' and not d.get('response'):
                    return True
                if isinstance(d.get('choices'), list) and len(d.get('choices')) > 0 and isinstance(d.get('choices')[0], dict):
                    fr = d.get('choices')[0].get('finish_reason') or d.get('choices')[0].get('done_reason')
                    txt = d.get('choices')[0].get('text') or ''
                    if fr == 'load' and not txt:
                        return True
                return False

            try:
                # `path` is the successful endpoint found above; retry it if loading
                if _is_loading_shape(data):
                    for attempt in range(3):
                        try:
                            time.sleep(0.8 * (attempt + 1))
                            d2 = self._post(path, payload, progress_callback=progress_callback)
                        except Exception:
                            d2 = None
                        if d2 and not _is_loading_shape(d2):
                            data = d2
                            break
            except Exception:
                pass
        except Exception:
            pass

        # If the successful endpoint returned a stream of JSON fragment
        # objects concatenated together (common when Ollama streams), try
        # to parse those fragments and assemble a single final text value
        # for the GUI to display cleanly.
        try:
            # Handle both `text` and Ollama's `response` key which some
            # Ollama HTTP endpoints return. Treat `response` similarly to
            # `text` when attempting to parse concatenated JSON fragments
            # produced by streaming responses.
            if isinstance(data, dict) and (isinstance(data.get('text'), str) or isinstance(data.get('response'), str)):
                raw_txt = (data.get('text') or data.get('response') or '')
                # Heuristic: multiple JSON lines or many fragment-ish keys
                if '\n{' in raw_txt or raw_txt.count('{"model"') > 1 or raw_txt.count('"message"') > 1:
                    fragments = []
                    parsed_any = False
                    for ln in raw_txt.splitlines():
                        s = ln.strip()
                        if not s:
                            continue
                        try:
                            obj = json.loads(s)
                            parsed_any = True
                            fragments.append(obj)
                        except Exception:
                            # ignore non-JSON lines
                            continue

                    if parsed_any and fragments:
                        parts = []
                        raw_frags = []
                        for frag in fragments:
                            if not isinstance(frag, dict):
                                continue
                            raw_frags.append(frag)
                            # common fragment shapes: message.content, response, text, choices[...] 
                            content = None
                            if isinstance(frag.get('message'), dict):
                                content = frag['message'].get('content')
                            if not content and frag.get('response'):
                                content = frag.get('response')
                            if not content and isinstance(frag.get('choices'), list) and frag['choices']:
                                first = frag['choices'][0]
                                if isinstance(first, dict):
                                    msg = first.get('message') or {}
                                    content = msg.get('content') or first.get('text') or first.get('content')
                            if not content and frag.get('text'):
                                content = frag.get('text')
                            if content:
                                parts.append(str(content))

                        assembled = ''.join(parts).strip()
                        if assembled:
                            data['assembled_text'] = assembled
                            data['raw_fragments'] = raw_frags
                            # If a progress callback was provided, stream
                            # incremental partials built from these fragments
                            # back to the caller so the UI can display
                            # interim content while generation progresses.
                            try:
                                if callable(progress_callback):
                                    parts_so_far = []
                                    total = len(raw_frags)
                                    for idx, frag in enumerate(raw_frags):
                                        # extract fragment content similarly to above
                                        content = None
                                        if isinstance(frag.get('message'), dict):
                                            content = frag['message'].get('content')
                                        if not content and frag.get('response'):
                                            content = frag.get('response')
                                        if not content and isinstance(frag.get('choices'), list) and frag['choices']:
                                            first = frag['choices'][0]
                                            if isinstance(first, dict):
                                                msg = first.get('message') or {}
                                                content = msg.get('content') or first.get('text') or first.get('content')
                                        if not content and frag.get('text'):
                                            content = frag.get('text')
                                        if content:
                                            parts_so_far.append(str(content))
                                        assembled_partial = ''.join(parts_so_far).strip()
                                        try:
                                            progress_callback('provider_stream', {'provider': self.name, 'partial': assembled_partial, 'fragment': frag, 'index': idx, 'total': total})
                                        except Exception:
                                            pass
                                    # After incremental streaming, emit a final assembled event
                                    try:
                                        if callable(progress_callback) and assembled:
                                            try:
                                                progress_callback('provider_stream', {'provider': self.name, 'partial': assembled, 'final': True, 'fragment': None, 'index': total-1 if isinstance(total, int) and total>0 else None, 'total': total})
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                            except Exception:
                                pass
        except Exception:
            # best-effort parsing; fall back to original behavior on any error
            pass

        text = ''
        tool_calls = []
        if isinstance(data, dict):
            # Prefer assembled_text (parsed from streaming JSON fragments) when available
            if isinstance(data.get('assembled_text'), str) and data.get('assembled_text'):
                text = data.get('assembled_text')
            # direct text
            elif isinstance(data.get('text'), str) and data.get('text'):
                text = data.get('text')
            # Some Ollama endpoints return `response` instead of `text`
            elif isinstance(data.get('response'), str) and data.get('response'):
                text = data.get('response')
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
