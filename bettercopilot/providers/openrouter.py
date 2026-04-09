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
import json

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

    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, system: Optional[str] = None, progress_callback: Optional[callable] = None, response_format: Optional[Dict[str, Any]] = None, stream: bool = False, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Call OpenRouter chat completions and return a normalized dict.

        Supports forwarding `tools`, `response_format`, and `stream`.
        If `stream=True` this will iterate the HTTP stream and call
        `progress_callback('provider_stream', {...})` with partial text.

        Returns a dict containing at least `text` and `raw` fields and
        optionally `tool_calls` and `diffs` (when the model returns
        structured edits/patches).
        """
        url = self.base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': self.model,
            'messages': messages,
        }
        if tools:
            payload['tools'] = tools
        if response_format:
            payload['response_format'] = response_format
        if max_tokens:
            payload['max_tokens'] = max_tokens
        if stream:
            payload['stream'] = True

        attempts = 0
        def _extract_text_from_obj(obj):
            """Recursively search common fields for text-like content and return a string.
            Returns None when nothing found.
            """
            try:
                if obj is None:
                    return None
                if isinstance(obj, (str, int, float)):
                    return str(obj)
                if isinstance(obj, dict):
                    for key in ('delta', 'content', 'text', 'message', 'output', 'final', 'preview'):
                        if key in obj and obj.get(key) is not None:
                            v = obj.get(key)
                            # Prefer to recurse into nested structures (common for 'delta')
                            if isinstance(v, (dict, list)):
                                try:
                                    res = _extract_text_from_obj(v)
                                    if res:
                                        return res
                                except Exception:
                                    pass
                                try:
                                    return json.dumps(v, ensure_ascii=False)
                                except Exception:
                                    return str(v)
                            return str(v)
                    # common nested shapes: choices -> [0] -> delta/message
                    if 'choices' in obj and isinstance(obj['choices'], list) and obj['choices']:
                        res = _extract_text_from_obj(obj['choices'][0])
                        if res:
                            return res
                    if 'message' in obj and isinstance(obj['message'], dict):
                        res = _extract_text_from_obj(obj['message'])
                        if res:
                            return res
                    # deeper search (best-effort)
                    for v in obj.values():
                        try:
                            res = _extract_text_from_obj(v)
                            if res:
                                return res
                        except Exception:
                            continue
                if isinstance(obj, list):
                    for item in obj:
                        res = _extract_text_from_obj(item)
                        if res:
                            return res
            except Exception:
                return None
            return None
        while attempts < 3:
            attempts += 1
            try:
                if stream:
                    with self.session.post(url, json=payload, stream=True, timeout=60) as resp:
                        resp.raise_for_status()
                        full_text = ''
                        raw_events = []
                        part_idx = 0
                        # Buffer SSE event lines until a blank line then process the event
                        event_lines: List[str] = []
                        for raw_line in resp.iter_lines(decode_unicode=True):
                            if raw_line is None:
                                continue
                            line = raw_line.decode() if isinstance(raw_line, bytes) else raw_line
                            # Normalize line endings
                            try:
                                line = line.rstrip('\r\n')
                            except Exception:
                                pass
                            # SSE comment lines are ignored
                            if line.startswith(':'):
                                continue
                            # Event boundary (blank line) -> process accumulated event_lines
                            if line.strip() == '':
                                if not event_lines:
                                    continue
                                # Combine data: lines into a single chunk
                                data_lines: List[str] = []
                                for l in event_lines:
                                    # Per SSE spec, only 'data:' lines are part of the event payload
                                    if l.startswith('data:'):
                                        payload = l[len('data:'):]
                                        # Remove a single leading space if present (the conventional separator), but preserve additional indentation
                                        if payload.startswith(' '):
                                            payload = payload[1:]
                                        data_lines.append(payload)
                                    else:
                                        # ignore other SSE fields (id:, event:, retry:, etc.)
                                        continue
                                # Do not aggressively strip the assembled payload; preserve indentation
                                chunk = '\n'.join(data_lines)
                                event_lines = []
                                if not chunk:
                                    continue
                                if chunk.strip() == '[DONE]':
                                    break
                                parsed = None
                                try:
                                    parsed = json.loads(chunk)
                                except Exception:
                                    parsed = None

                                if parsed is not None:
                                    raw_events.append(parsed)
                                    # extract incremental delta/text using helper
                                    delta = _extract_text_from_obj(parsed)
                                    if delta is not None:
                                        try:
                                            if isinstance(delta, (dict, list)):
                                                delta_str = json.dumps(delta, ensure_ascii=False)
                                            else:
                                                delta_str = str(delta)
                                        except Exception:
                                            delta_str = str(delta)
                                        full_text += delta_str
                                        try:
                                            if callable(progress_callback):
                                                # send only the incremental delta to reduce payloads
                                                progress_callback('provider_stream', {'provider': self.name, 'partial': delta_str, 'index': part_idx, 'total': None})
                                        except Exception:
                                            pass
                                        part_idx += 1
                                else:
                                    # Try parsing chunk as multiple JSON-lines; handle mixed JSON/text
                                    any_parsed = False
                                    for line_part in chunk.splitlines():
                                        lp = line_part.strip()
                                        if not lp:
                                            continue
                                        if lp == '[DONE]':
                                            any_parsed = True
                                            break
                                        try:
                                            parsed_line = json.loads(lp)
                                            any_parsed = True
                                            raw_events.append(parsed_line)
                                            delta = _extract_text_from_obj(parsed_line)
                                            if delta is not None:
                                                try:
                                                    delta_str = json.dumps(delta, ensure_ascii=False) if isinstance(delta, (dict, list)) else str(delta)
                                                except Exception:
                                                    delta_str = str(delta)
                                                full_text += delta_str
                                                try:
                                                    if callable(progress_callback):
                                                        progress_callback('provider_stream', {'provider': self.name, 'partial': delta_str, 'index': part_idx, 'total': None})
                                                except Exception:
                                                    pass
                                                part_idx += 1
                                            else:
                                                try:
                                                    parsed_text = json.dumps(parsed_line, ensure_ascii=False) if isinstance(parsed_line, (dict, list)) else str(parsed_line)
                                                except Exception:
                                                    parsed_text = str(parsed_line)
                                                full_text += parsed_text
                                                try:
                                                    if callable(progress_callback):
                                                        progress_callback('provider_stream', {'provider': self.name, 'partial': parsed_text, 'index': part_idx, 'total': None})
                                                except Exception:
                                                    pass
                                                part_idx += 1
                                        except Exception:
                                            # treat as a text line
                                            try:
                                                chunk_text = line_part if isinstance(line_part, str) else json.dumps(line_part, ensure_ascii=False)
                                            except Exception:
                                                chunk_text = str(line_part)
                                            full_text += chunk_text
                                            raw_events.append(chunk_text)
                                            try:
                                                if callable(progress_callback):
                                                    progress_callback('provider_stream', {'provider': self.name, 'partial': chunk_text, 'index': part_idx, 'total': None})
                                            except Exception:
                                                pass
                                            part_idx += 1

                                    if any_parsed:
                                        # we've handled the chunk by per-line parsing
                                        continue
                                    # fallback: non-JSON chunk, treat as plain text
                                    try:
                                        chunk_text = chunk if isinstance(chunk, str) else json.dumps(chunk, ensure_ascii=False)
                                    except Exception:
                                        chunk_text = str(chunk)
                                    full_text += chunk_text
                                    raw_events.append(chunk_text)
                                    try:
                                        if callable(progress_callback):
                                            progress_callback('provider_stream', {'provider': self.name, 'partial': chunk_text, 'index': part_idx, 'total': None})
                                    except Exception:
                                        pass
                                    part_idx += 1
                            else:
                                # Accumulate lines for the current event
                                event_lines.append(line)

                        # If any leftover lines after streaming ends, process them
                        if event_lines:
                            data_lines = []
                            for l in event_lines:
                                if l.startswith('data:'):
                                        payload = l[len('data:'):]
                                        if payload.startswith(' '):
                                            payload = payload[1:]
                                        data_lines.append(payload)
                            chunk = '\n'.join(data_lines)
                            if chunk and chunk.strip() != '[DONE]':
                                try:
                                    parsed = json.loads(chunk)
                                except Exception:
                                    parsed = None

                                if parsed is not None:
                                    raw_events.append(parsed)
                                    delta = _extract_text_from_obj(parsed)
                                    if delta is not None:
                                        try:
                                            delta_str = json.dumps(delta, ensure_ascii=False) if isinstance(delta, (dict, list)) else str(delta)
                                        except Exception:
                                            delta_str = str(delta)
                                        full_text += delta_str
                                else:
                                    # attempt per-line parsing for leftover block
                                    any_parsed = False
                                    for line_part in chunk.splitlines():
                                        lp = line_part.strip()
                                        if not lp:
                                            continue
                                        try:
                                            parsed_line = json.loads(lp)
                                            any_parsed = True
                                            raw_events.append(parsed_line)
                                            delta = _extract_text_from_obj(parsed_line)
                                            if delta is not None:
                                                try:
                                                    delta_str = json.dumps(delta, ensure_ascii=False) if isinstance(delta, (dict, list)) else str(delta)
                                                except Exception:
                                                    delta_str = str(delta)
                                                full_text += delta_str
                                        except Exception:
                                            try:
                                                chunk_text = line_part if isinstance(line_part, str) else json.dumps(line_part, ensure_ascii=False)
                                            except Exception:
                                                chunk_text = str(line_part)
                                            full_text += chunk_text
                                            raw_events.append(chunk_text)
                                    if not any_parsed:
                                        try:
                                            chunk_text = chunk if isinstance(chunk, str) else json.dumps(chunk, ensure_ascii=False)
                                        except Exception:
                                            chunk_text = str(chunk)
                                        full_text += chunk_text

                        text = full_text
                        raw = raw_events or {}
                else:
                    resp = self.session.post(url, json=payload, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                    raw = data
                    # Extract text from common OpenRouter/OpenAI-like shapes
                    text = ''
                    choices = data.get('choices') if isinstance(data, dict) else None
                    if choices and len(choices) > 0:
                        ch = choices[0]
                        if isinstance(ch, dict):
                            message = ch.get('message') or {}
                            if isinstance(message, dict):
                                content = message.get('content') if 'content' in message else message.get('text') or ch.get('text')
                                # normalize structured content to string
                                try:
                                    if isinstance(content, (dict, list)):
                                        text = json.dumps(content, ensure_ascii=False)
                                    else:
                                        text = str(content or '')
                                except Exception:
                                    text = str(content)
                            else:
                                text = str(ch.get('text') or '')
                        else:
                            text = str(ch)
                    else:
                        if isinstance(data, dict) and 'output' in data:
                            out = data.get('output')
                            if isinstance(out, str):
                                text = out
                            elif isinstance(out, dict):
                                # normalize dict output
                                try:
                                    text = json.dumps(out, ensure_ascii=False)
                                except Exception:
                                    text = str(out)

                # If streaming, raw may be a list of parsed events; scan for structured diffs/patches
                stream_diffs = None
                try:
                    if isinstance(raw, list) and raw:
                        for ev in raw:
                            # Normalize event container into iterable items we can inspect
                            items = [ev]
                            # If the event itself is a JSON string, try to parse it
                            if isinstance(ev, str):
                                try:
                                    ev_parsed = json.loads(ev)
                                    items = [ev_parsed]
                                except Exception:
                                    items = [ev]
                            # If the event is a list (e.g. list of diffs), inspect each element
                            if isinstance(ev, list):
                                items = ev

                            for it in items:
                                candidate = it
                                if isinstance(candidate, str):
                                    try:
                                        candidate = json.loads(candidate)
                                    except Exception:
                                        pass
                                if isinstance(candidate, dict):
                                    if 'diffs' in candidate:
                                        stream_diffs = candidate.get('diffs')
                                        break
                                    if 'patch' in candidate or 'diff' in candidate or 'patch_text' in candidate:
                                        stream_diffs = candidate.get('patch') or candidate.get('diff') or candidate.get('patch_text')
                                        break
                                    if 'file_edits' in candidate:
                                        stream_diffs = candidate.get('file_edits')
                                        break
                        # end for
                except Exception:
                    stream_diffs = None

                # Try to parse structured JSON out of the returned text to find diffs/patch
                diffs = stream_diffs
                parsed_json = None
                try:
                    parsed_json = json.loads(text)
                except Exception:
                    try:
                        start = text.find('{')
                        end = text.rfind('}')
                        if start != -1 and end != -1 and end > start:
                            parsed_json = json.loads(text[start:end+1])
                    except Exception:
                        parsed_json = None
                if parsed_json and isinstance(parsed_json, dict):
                    if 'diffs' in parsed_json:
                        diffs = parsed_json.get('diffs')
                    elif 'patch' in parsed_json:
                        diffs = parsed_json.get('patch')
                    elif 'file_edits' in parsed_json:
                        diffs = parsed_json.get('file_edits')

                # Normalize diffs into a list of strings for consistent consumers
                diffs_list: List[str] = []
                try:
                    if diffs is None:
                        diffs_list = []
                    elif isinstance(diffs, str):
                        diffs_list = [diffs]
                    elif isinstance(diffs, dict):
                        try:
                            diffs_list = [json.dumps(diffs, ensure_ascii=False)]
                        except Exception:
                            diffs_list = [str(diffs)]
                    elif isinstance(diffs, list):
                        new_list = []
                        for d in diffs:
                            if isinstance(d, (dict, list)):
                                try:
                                    new_list.append(json.dumps(d, ensure_ascii=False))
                                except Exception:
                                    new_list.append(str(d))
                            else:
                                new_list.append(str(d))
                        diffs_list = new_list
                    else:
                        diffs_list = [str(diffs)]
                except Exception:
                    diffs_list = [str(diffs)]

                # Fallback: detect unified diff in text and add to list
                try:
                    probe_text = text or ''
                    if isinstance(probe_text, str) and ('diff --git' in probe_text or ('--- ' in probe_text and '+++ ' in probe_text and '\n@@ ' in probe_text)):
                        diffs_list.append(probe_text)
                except Exception:
                    pass

                tool_calls = None
                if isinstance(raw, dict):
                    tool_calls = raw.get('tool_calls') or []
                else:
                    tool_calls = []
                out = {'text': text or '', 'tool_calls': tool_calls, 'raw': raw}
                if diffs_list:
                    out['diffs'] = diffs_list
                return out
            except Exception as e:
                self.logger.exception('OpenRouter request failed (attempt %d): %s', attempts, e)
                time.sleep(0.5 * attempts)

        return {'text': '', 'tool_calls': [], 'raw': {'error': 'openrouter_failed'}}
