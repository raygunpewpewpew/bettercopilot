"""Thin GUI -> Orchestrator API wrapper.

This module provides convenience functions used by the GUI to run tasks
via the orchestrator without blocking the GUI thread.
"""
from typing import Optional, Dict, Any
import json
import re
import time
from pathlib import Path
from .worker import Worker
from bettercopilot.orchestrator.task import Task
from bettercopilot.orchestrator.orchestrator import Orchestrator
from bettercopilot.providers.ollama_local import OllamaLocalProvider
from bettercopilot.mcp.registry import MCPRegistry
import uuid
import os
import threading

try:
    # Import provider module but do not instantiate unless key present
    from bettercopilot.providers.openrouter import OpenRouterProvider
except Exception:
    OpenRouterProvider = None

try:
    # Prefer an HTTP-backed Ollama provider when available
    from bettercopilot.providers.ollama_http import OllamaHTTPProvider
except Exception:
    OllamaHTTPProvider = None


def _make_orchestrator(progress_callback=None):
    providers = {}
    # Prefer OpenRouter when API key is set in environment
    try:
        key = os.getenv('OPENROUTER_API_KEY')
        if key and OpenRouterProvider is not None:
            try:
                providers['openrouter'] = OpenRouterProvider(api_key=key)
            except Exception:
                pass
    except Exception:
        pass

    # Prefer an HTTP-backed Ollama provider when available. If the
    # environment explicitly sets OLLAMA_URL/OLLAMA_HOST, use that. Otherwise
    # perform a lightweight probe of the default local endpoint and prefer
    # the HTTP provider if the server is reachable.
    try:
        if OllamaHTTPProvider is not None:
            ollama_url = os.getenv('OLLAMA_URL') or os.getenv('OLLAMA_HOST')
            if ollama_url:
                try:
                    providers['ollama'] = OllamaHTTPProvider(api_url=ollama_url)
                except Exception:
                    pass
            else:
                try:
                    # Try default local Ollama and probe availability quickly
                    candidate = OllamaHTTPProvider()
                    try:
                        if candidate.is_available(timeout=0.8):
                            providers['ollama'] = candidate
                    except Exception:
                        pass
                except Exception:
                    pass
    except Exception:
        pass

    # Always include the simulated local provider as a fallback if no HTTP Ollama
    if 'ollama' not in providers and 'ollama_local' not in providers:
        providers['ollama_local'] = OllamaLocalProvider()

    registry = MCPRegistry()
    return Orchestrator(providers, registry, progress_callback=progress_callback)


def _connect_signal_to_ui(signal, handler):
    """Connect a worker signal to a handler and ensure the handler runs on the
    Qt main thread when PySide6 is available. Falls back to direct connect.
    """
    try:
        from PySide6.QtCore import QTimer, QCoreApplication

        # If no Qt application instance is running (headless/testing), avoid
        # scheduling via QTimer.singleShot() because the event loop won't run.
        app = QCoreApplication.instance()
        # If no Qt application instance is running (headless/testing), connect directly.
        if app is None:
            try:
                signal.connect(handler)
                return
            except Exception:
                pass

        # If Qt exists but its thread/event loop isn't running, avoid queuing callbacks.
        try:
            thr = app.thread()
            if hasattr(thr, 'isRunning') and not thr.isRunning():
                try:
                    signal.connect(handler)
                    return
                except Exception:
                    pass
        except Exception:
            pass

        def _wrapper(*a, **k):
            try:
                QTimer.singleShot(0, lambda: handler(*a, **k))
            except Exception:
                try:
                    handler(*a, **k)
                except Exception:
                    pass

        try:
            signal.connect(_wrapper)
            return
        except Exception:
            # fall through to direct connect
            pass
    except Exception:
        pass

    try:
        signal.connect(handler)
    except Exception:
        try:
            # Last-resort: ignore connection failures
            pass
        except Exception:
            pass


def _write_debug_line(s: str, max_bytes: int = 5 * 1024 * 1024) -> bool:
    """Write a debug JSON line to disk using several candidate locations.

    Returns True if write succeeded.
    """
    # Prefer the centralized global_debug when available
    try:
        from bettercopilot.logging import global_debug
        try:
            obj = None
            try:
                obj = json.loads(s)
            except Exception:
                obj = {'ts': time.time(), 'event': 'debug_line', 'text': s}
            return bool(global_debug.write(obj))
        except Exception:
            pass
    except Exception:
        pass

    # Fallback: write to local debug_log.txt candidates (legacy behavior)
    candidates = [Path.cwd()]
    try:
        pkg_root = Path(__file__).resolve().parents[4]
        candidates.append(pkg_root)
    except Exception:
        pass
    candidates.append(Path.home())

    for base in candidates:
        try:
            logfile = Path(base) / 'DebugLogs' / 'debug_log.txt'
            # rotate if necessary
            try:
                b = len(s.encode('utf-8')) + 1
                if logfile.exists() and logfile.stat().st_size + b > max_bytes:
                    rotated = logfile.with_name(f"{logfile.stem}_{time.strftime('%Y%m%d_%H%M%S')}.txt")
                    try:
                        logfile.replace(rotated)
                    except Exception:
                        try:
                            logfile.rename(rotated)
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                logfile.parent.mkdir(parents=True, exist_ok=True)
                with open(logfile, 'a', encoding='utf-8') as f:
                    f.write(s + "\n")
                return True
            except Exception:
                continue
        except Exception:
            continue

    return False


def _extract_json_from_string(s: Optional[str]):
    """Attempt to locate and parse a JSON object/array inside a string.

    Returns the parsed JSON or None on failure.
    """
    if not s or not isinstance(s, str):
        return None
    st = s.strip()
    # direct parse
    try:
        return json.loads(st)
    except Exception:
        pass

    # look for fenced code block containing JSON ```json ... ```
    try:
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', st, re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            try:
                return json.loads(cand)
            except Exception:
                pass
    except Exception:
        pass

    # try to locate the first balanced JSON object {...}
    try:
        start = st.find('{')
        if start != -1:
            depth = 0
            for i in range(start, len(st)):
                ch = st[i]
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        cand = st[start:i+1]
                        try:
                            return json.loads(cand)
                        except Exception:
                            break
    except Exception:
        pass

    # try to locate the first balanced JSON array [...]
    try:
        start = st.find('[')
        if start != -1:
            depth = 0
            for i in range(start, len(st)):
                ch = st[i]
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        cand = st[start:i+1]
                        try:
                            return json.loads(cand)
                        except Exception:
                            break
    except Exception:
        pass

    return None


def run_task(task: Task, callback=None, error_callback=None) -> Worker:
    orch = _make_orchestrator()
    worker = Worker(orch.run_task, task)

    def _finished_handler(res):
        try:
            if callback:
                callback(res)
        except Exception as e:
            try:
                _write_debug_line(json.dumps({'ts': time.time(), 'event': 'run_task_callback_exception', 'error': str(e)}))
            except Exception:
                pass

    def _error_handler(err):
        try:
            if error_callback:
                error_callback(err)
        except Exception as e:
            try:
                _write_debug_line(json.dumps({'ts': time.time(), 'event': 'run_task_error', 'error': str(e)}))
            except Exception:
                pass

    try:
        _connect_signal_to_ui(worker.finished, _finished_handler)
    except Exception:
        try:
            worker.finished.connect(_finished_handler)
        except Exception:
            pass

    try:
        _connect_signal_to_ui(worker.error, _error_handler)
    except Exception:
        try:
            worker.error.connect(_error_handler)
        except Exception:
            pass

    worker.start()
    return worker


def run_ask(goal: str, callback=None, error_callback=None) -> Worker:
    # Prefer OpenRouter explicitly when it's configured in the orchestrator.
    t = Task(id=str(uuid.uuid4()), goal=goal)
    orch = _make_orchestrator()
    if hasattr(orch, 'providers') and 'openrouter' in orch.providers:
        t.provider = 'openrouter'
    # Run using the constructed orchestrator so we don't re-create providers.
    worker = Worker(orch.run_task, t)

    def _finished_handler(res):
        try:
            if callback:
                callback(res)
        except Exception:
            pass

    def _error_handler(err):
        try:
            if error_callback:
                error_callback(err)
        except Exception:
            pass

    try:
        _connect_signal_to_ui(worker.finished, _finished_handler)
    except Exception:
        try:
            worker.finished.connect(_finished_handler)
        except Exception:
            pass

    try:
        _connect_signal_to_ui(worker.error, _error_handler)
    except Exception:
        try:
            worker.error.connect(_error_handler)
        except Exception:
            pass

    worker.start()
    return worker


def run_fix(path: str, callback=None, error_callback=None) -> Worker:
    t = Task(id=str(uuid.uuid4()), goal=f"Fix file {path}")
    return run_task(t, callback=callback, error_callback=error_callback)


def run_rom_analysis(path: str, callback=None, error_callback=None) -> Worker:
    t = Task(id=str(uuid.uuid4()), goal=f"Analyze ROM {path}", tools=['fusion_inspect'])
    return run_task(t, callback=callback, error_callback=error_callback)


class GUIAPI:
    """High-level API object the GUI can bind to.

    Methods are designed to be simple and to update bound frontend panels
    when worker results arrive. Bind the frontend via `bind_frontend(mainwin)`
    where `mainwin` exposes `editor`, `file_tree`, `ai_panel`, `diff_viewer`,
    and `status_bar` attributes.
    """

    def __init__(self, orchestrator: Optional[Orchestrator] = None):
        # If no orchestrator provided, build one that reports progress
        if orchestrator is None:
            self.orchestrator = _make_orchestrator(progress_callback=self._handle_progress)
        else:
            self.orchestrator = orchestrator
            try:
                # Ensure provided orchestrator reports progress to this GUI
                setattr(self.orchestrator, 'progress_callback', self._handle_progress)
            except Exception:
                pass
        self.editor = None
        self.file_tree = None
        self.ai_panel = None
        self.diff_viewer = None
        self.status_bar = None
        # autosave controls whether applied patches are saved automatically.
        # False = prompt (default), True = autosave without prompting.
        self.autosave = False
        # If True, send user messages directly to a provider (fast chat),
        # otherwise use the full orchestrator pipeline.
        self.direct_chat = True
        # If True, automatically apply AI-generated diffs/patches to the editor
        # when a task result contains `diffs`. Default: False (require review).
        self.auto_apply_edits = False
        # When True, instruct providers to return only JSON responses. The UI
        # will parse the JSON and route `chat` -> AI panel, `diff`/`diffs` -> Diff Viewer.
        self.force_json_output = True
        # When True, enforce that file edits are placed in `diff`/`diffs` fields
        # of provider JSON responses; attempts will be made to move patch-like
        # content out of `chat` and into `diffs` for consistent handling.
        self.enforce_diff_in_json = True

    def _json_output_instruction(self) -> str:
        return (
            'IMPORTANT: Respond with a single, valid JSON object and nothing else. '
            'The object MUST include the key "chat" with a short human-readable summary. '
            'Any file edits MUST be provided exclusively in the "diff" (string) or "diffs" (array) fields as unified diffs. '
            'Do NOT place file-edit content inside "chat". Do not include any explanatory text, markdown fences, or other content outside the JSON object.'
        )
    def _looks_like_unified_diff(self, s: Optional[str]) -> bool:
        """Heuristic test for unified diff / patch text.

        Returns True if the string contains markers typical of unified diffs.
        """
        try:
            if not s or not isinstance(s, str):
                return False
            # common markers
            if 'diff --git' in s:
                return True
            if s.strip().startswith('--- ') and '\n' in s and '+++ ' in s:
                return True
            if '\n@@ ' in s or s.strip().startswith('@@ '):
                return True
            # fallback: chunk headers
            if s.strip().startswith('*** ') and '\n*** ' in s:
                return True
        except Exception:
            return False
        return False

    def bind_frontend(self, frontend):
        # frontend expected to be MainWindow or HeadlessMainWindow
        self.editor = getattr(frontend, 'editor', None)
        self.file_tree = getattr(frontend, 'file_tree', None)
        self.ai_panel = getattr(frontend, 'ai_panel', None)
        self.ai_panel_ollama = getattr(frontend, 'ai_panel_ollama', None)
        self.diff_viewer = getattr(frontend, 'diff_viewer', None)
        self.status_bar = getattr(frontend, 'status_bar', None)
        # Report which providers were loaded so the user can verify configuration
        try:
            provs = []
            if hasattr(self, 'orchestrator') and getattr(self.orchestrator, 'providers', None):
                provs = list(self.orchestrator.providers.keys())
            if provs:
                try:
                    msg = f"Providers: {', '.join(provs)}"
                    if self.ai_panel:
                        try:
                            self.ai_panel.append_message('status', msg)
                        except Exception:
                            pass
                    if self.ai_panel_ollama:
                        try:
                            self.ai_panel_ollama.append_message('status', msg)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        # If an Ollama HTTP provider is present, probe for available models
        try:
            if getattr(self, 'ai_panel_ollama', None) and hasattr(self.orchestrator, 'providers') and 'ollama' in (self.orchestrator.providers or {}):
                try:
                    prov = self.orchestrator.providers.get('ollama')
                    # If provider exposes `list_models`, call it and populate the combo
                    if prov and hasattr(prov, 'list_models') and callable(getattr(prov, 'list_models')):
                        try:
                            models = prov.list_models()
                            try:
                                sel = getattr(prov, 'model', None)
                            except Exception:
                                sel = None
                            try:
                                self.ai_panel_ollama.set_model_list(models or [], selected=sel)
                            except Exception:
                                pass
                        except Exception:
                            pass
                    # connect selection change back to provider
                    try:
                        def _on_model_selected(m):
                            try:
                                if prov:
                                    try:
                                        prov.model = m
                                    except Exception:
                                        try:
                                            setattr(prov, 'model', m)
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                        try:
                            self.ai_panel_ollama.model_selected.connect(_on_model_selected)
                        except Exception:
                            try:
                                # headless signal
                                self.ai_panel_ollama.model_selected.connect(_on_model_selected)
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

    def set_direct_chat(self, enabled: bool):
        """Enable or disable direct provider chat mode."""
        try:
            self.direct_chat = bool(enabled)
            if self.ai_panel:
                try:
                    self.ai_panel.append_message('status', f"Direct provider chat: {'on' if self.direct_chat else 'off'}")
                except Exception:
                    pass
        except Exception:
            pass

    def get_direct_chat(self) -> bool:
        return bool(getattr(self, 'direct_chat', False))

    def open_file(self, path: str):
        if self.editor:
            try:
                self.editor.load_file(path)
                if self.ai_panel:
                    self.ai_panel.append_message('system', f'Opened {path}')
                # Log file-open to centralized debug
                try:
                    from bettercopilot.logging import global_debug
                    try:
                        global_debug.write({'ts': time.time(), 'event': 'file_open', 'path': path})
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                if self.status_bar:
                    self.status_bar.set_message(f'Failed to open {path}')

    def _on_task_finished(self, result: Dict[str, Any], origin: str = 'task', panel=None):
        # Update UI panels with result
        if not isinstance(result, dict):
            return

        def _extract_text(res: Dict[str, Any]) -> Optional[str]:
            # Prefer explicit final_text
            if res.get('final_text'):
                return res.get('final_text')
            # direct text field
            if res.get('text'):
                return res.get('text')

            # Look through logs for an output_preview or corrected_code
            for entry in reversed(res.get('logs') or []):
                if not isinstance(entry, dict):
                    continue
                if 'output_preview' in entry and entry.get('output_preview'):
                    return entry.get('output_preview')
                pa = entry.get('policy_assessment') or entry.get('policy_assessment')
                if isinstance(pa, dict):
                    cc = pa.get('corrected_code')
                    if cc:
                        return cc
                # Some runs may include a provider 'message' shape in logs
                if 'message' in entry and isinstance(entry.get('message'), dict):
                    m = entry.get('message')
                    if m.get('content'):
                        return m.get('content')

            # Check critic_feedback for corrected_code
            for cf in reversed(res.get('critic_feedback') or []):
                if isinstance(cf, dict) and cf.get('corrected_code'):
                    return cf.get('corrected_code')

            # Fallback: inspect raw provider shape
            raw = res.get('raw') or {}
            if isinstance(raw, dict):
                choices = raw.get('choices')
                if isinstance(choices, list) and len(choices) > 0:
                    ch = choices[0]
                    if isinstance(ch, dict):
                        msg = ch.get('message') or {}
                        if isinstance(msg, dict) and msg.get('content'):
                            return msg.get('content')
                        if ch.get('text'):
                            return ch.get('text')
                if 'output' in raw:
                    out = raw.get('output')
                    if isinstance(out, str):
                        return out
                    if isinstance(out, dict) and out.get('text'):
                        return out.get('text')

            return None

        final = _extract_text(result)
        # Debug: log final text to console to help diagnose missing UI responses
        try:
            if final:
                try:
                    print(f"[GUIAPI] _on_task_finished final (source={origin}): {str(final)[:200]}")
                except Exception:
                    pass
        except Exception:
            pass
        # Use module-level JSON extraction helper so feedback loop can reuse it
        # (function defined at module scope: `_extract_json_from_string`).

        parsed_diffs = None
        try:
            parsed_json = None
            try:
                parsed_json = _extract_json_from_string(final) if isinstance(final, str) else None
            except Exception:
                parsed_json = None

            # fallback: try to parse raw provider output if final didn't contain JSON
            if parsed_json is None:
                raw = result.get('raw')
                if isinstance(raw, str):
                    try:
                        parsed_json = _extract_json_from_string(raw)
                    except Exception:
                        parsed_json = None
                elif isinstance(raw, dict):
                    # provider may return JSON structure directly under raw
                    if any(k in raw for k in ('chat', 'diff', 'diffs', 'patch')):
                        parsed_json = raw
                    else:
                        # inspect common nested shapes like choices[] -> message -> content
                        try:
                            choices = raw.get('choices')
                            if isinstance(choices, list):
                                for ch in choices:
                                    if isinstance(ch, dict):
                                        msg = ch.get('message') or ch.get('content') or ch.get('text')
                                        if isinstance(msg, str):
                                            pj = _extract_json_from_string(msg)
                                            if pj is not None:
                                                parsed_json = pj
                                                break
                        except Exception:
                            pass

            if isinstance(parsed_json, dict):
                # Extract chat text when present
                try:
                    if 'chat' in parsed_json and isinstance(parsed_json.get('chat'), str):
                        final = parsed_json.get('chat')
                except Exception:
                    pass

                # Extract diffs under several possible keys
                try:
                    if 'diff' in parsed_json:
                        parsed_diffs = parsed_json.get('diff')
                    elif 'diffs' in parsed_json:
                        parsed_diffs = parsed_json.get('diffs')
                    elif 'patch' in parsed_json:
                        parsed_diffs = parsed_json.get('patch')
                except Exception:
                    parsed_diffs = None
                # If configured, and `chat` contains what looks like a unified
                # diff/patch, move it into parsed_diffs so edits are treated as
                # file output rather than conversation text.
                try:
                    if getattr(self, 'enforce_diff_in_json', False):
                        try:
                            c = parsed_json.get('chat') if isinstance(parsed_json.get('chat'), str) else None
                            if c and parsed_diffs is None and _looks_like_unified_diff(c):
                                parsed_diffs = c
                                # replace chat with a short summary to avoid flooding UI
                                try:
                                    parsed_json['chat'] = 'Provided patch moved to diff field.'
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            parsed_diffs = None
        diffs = result.get('diffs') or []
        # Normalize diffs to a list of strings for consistent downstream handling
        try:
            if isinstance(diffs, str):
                diffs = [diffs]
            elif isinstance(diffs, dict):
                try:
                    diffs = [json.dumps(diffs, ensure_ascii=False)]
                except Exception:
                    diffs = [str(diffs)]
            elif not isinstance(diffs, list):
                try:
                    diffs = list(diffs)
                except Exception:
                    diffs = [str(diffs)]
        except Exception:
            diffs = [str(diffs)]
        # If we parsed diffs out of a JSON final payload, prefer those.
        try:
            if parsed_diffs is not None:
                if isinstance(parsed_diffs, list):
                    diffs = parsed_diffs
                else:
                    diffs = [parsed_diffs]
        except Exception:
            pass
        # If we parsed a JSON payload that included a chat message, show
        # the chat text in the response panel immediately (do not apply
        # it to the editor as a final_text patch).
        try:
            if 'parsed_json' in locals() and parsed_json is not None and isinstance(parsed_json, dict) and parsed_json.get('chat'):
                try:
                    tgt_panel = panel or self.ai_panel
                    if tgt_panel and hasattr(tgt_panel, 'append_message'):
                        try:
                            tgt_panel.append_message('assistant', parsed_json.get('chat'))
                        except Exception:
                            tgt_panel.append_message('assistant', str(parsed_json.get('chat')))
                except Exception:
                    pass
        except Exception:
            pass
        logs = result.get('logs') or []

        target_panel = panel or self.ai_panel

        # If diffs present, treat them as file edits (prioritize unified 'patch')
        # and display the patch in the Diff Viewer. The assistant's final
        # message is still shown in the AI panel for context; edits must be
        # explicitly applied by the user unless `auto_apply_edits` is enabled.
        try:
            if diffs:
                diff_obj = diffs[-1]
                diff_text = None
                try:
                    if isinstance(diff_obj, dict):
                        # Prefer unified diff text under common keys
                        diff_text = diff_obj.get('patch') or diff_obj.get('diff') or diff_obj.get('patch_text') or diff_obj.get('final_text')
                        # If value is not a string, stringify the dict as a fallback
                        if diff_text is None:
                            try:
                                diff_text = json.dumps(diff_obj, ensure_ascii=False)
                            except Exception:
                                diff_text = str(diff_obj)
                    else:
                        diff_text = str(diff_obj)
                except Exception:
                    try:
                        diff_text = json.dumps(diff_obj, ensure_ascii=False)
                    except Exception:
                        diff_text = str(diff_obj)

                # Show diff in the diff viewer as text
                try:
                    if self.diff_viewer is not None:
                        try:
                            self.diff_viewer.set_diff(diff_text)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Notify panel about edits (status only)
                try:
                    if target_panel and hasattr(target_panel, 'append_message'):
                        try:
                            target_panel.append_message('status', 'AI produced file edits (see Diff Viewer)')
                        except Exception:
                            pass
                except Exception:
                    pass

                # Auto-apply if enabled (default: False)
                try:
                    if getattr(self, 'auto_apply_edits', False) and self.editor:
                        try:
                            if isinstance(diff_obj, dict):
                                patch_text = diff_obj.get('patch') or diff_obj.get('diff') or diff_obj.get('patch_text')
                                final_text = diff_obj.get('final_text') if isinstance(diff_obj, dict) else None
                                if patch_text:
                                    try:
                                        self.editor.apply_diff(diff_text=patch_text, final_text=final_text)
                                    except Exception:
                                        if final_text:
                                            try:
                                                self.editor.apply_diff(final_text=final_text)
                                            except Exception:
                                                pass
                                elif final_text:
                                    try:
                                        self.editor.apply_diff(final_text=final_text)
                                    except Exception:
                                        pass
                            else:
                                try:
                                    self.editor.apply_diff(diff_text=diff_text)
                                except Exception:
                                    pass

                            if getattr(self, 'autosave', False):
                                try:
                                    self.editor.save_file()
                                except Exception:
                                    pass

                            try:
                                if target_panel:
                                    target_panel.append_message('status', 'Applied AI edits to editor' + (' and saved' if getattr(self, 'autosave', False) else ''))
                            except Exception:
                                pass
                        except Exception:
                            pass
                except Exception:
                    pass

                # keep assistant final text available even when diffs exist
                pass
        except Exception:
            pass

        if final:
            # Decide whether this final text is provider/chat output (route to AI panel)
            def _extract_provider_name(res: Dict[str, Any]):
                try:
                    for entry in (res.get('logs') or []):
                        if isinstance(entry, dict):
                            prov = (entry.get('provider') or entry.get('provider_name') or '')
                            if isinstance(prov, str) and prov:
                                pl = prov.lower()
                                if 'openrouter' in pl:
                                    return 'openrouter'
                                if 'ollama' in pl:
                                    return 'ollama'
                    raw = res.get('raw') or {}
                    if isinstance(raw, dict):
                        try:
                            rs = json.dumps(raw, ensure_ascii=False).lower()
                            if 'openrouter' in rs:
                                return 'openrouter'
                            if 'ollama' in rs:
                                return 'ollama'
                        except Exception:
                            pass
                except Exception:
                    pass
                return None

            provider_name = None
            try:
                if origin == 'direct':
                    # prefer explicit provider hint in logs when direct
                    try:
                        logs = result.get('logs') or []
                        if isinstance(logs, list) and len(logs) > 0 and isinstance(logs[0], dict):
                            provider_name = (logs[0].get('provider') or logs[0].get('provider_name') or None)
                    except Exception:
                        provider_name = None
                    if not provider_name:
                        provider_name = _extract_provider_name(result)
                else:
                    provider_name = _extract_provider_name(result)
            except Exception:
                provider_name = None

            is_provider_out = bool(provider_name)

            if is_provider_out:
                # Route chat reply to the originating AI panel when possible
                try:
                    if panel:
                        tgt = panel
                    else:
                        if provider_name and 'ollama' in provider_name.lower() and getattr(self, 'ai_panel_ollama', None):
                            tgt = self.ai_panel_ollama
                        else:
                            tgt = self.ai_panel
                    if tgt and hasattr(tgt, 'append_message'):
                        try:
                            tgt.append_message('assistant', final)
                        except Exception:
                            pass
                    else:
                        try:
                            dbg = {'ts': time.time(), 'event': 'provider_final', 'provider': provider_name, 'final': (final or '')[:1000]}
                            _write_debug_line(json.dumps(dbg, ensure_ascii=False))
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                # Non-provider final results are applied to the editor as before
                if self.editor:
                    try:
                        self.editor.apply_diff(final_text=final)
                    except Exception:
                        pass

        if self.status_bar:
            self.status_bar.set_message(f'Completed: {origin}')

    def _on_task_error(self, err: Exception):
        if self.status_bar:
            try:
                self.status_bar.set_message(f'Error: {str(err)}')
            except Exception:
                pass

    def _set_status(self, text: str):
        try:
            if self.status_bar:
                self.status_bar.set_message(text)
        except Exception:
            pass
        try:
            if self.ai_panel and hasattr(self.ai_panel, 'set_status'):
                self.ai_panel.set_status(text)
        except Exception:
            pass

    def _handle_progress(self, event: str, data: Optional[Dict[str, Any]] = None):
        # Map orchestrator events to friendly status messages and append
        # helpful feedback to the AI panel (provider previews, interim status).
        try:
            print(f"[GUIAPI] _handle_progress invoked event={event} data_type={type(data)}")
        except Exception:
            pass
        mapping = {
            'task_start': 'Prompt sent',
            'provider_call_start': 'Thinking...',
            'provider_call_end': 'Evaluating...',
            'critic_start': 'Evaluating...',
            'critic_end': 'Responding...',
            'policy_assessment_start': 'Evaluating...',
            'policy_assessment_end': 'Responding...',
            'responding': 'Responding...',
            'provider_error': 'Provider error',
            'done': 'Done',
        }
        status = mapping.get(event, str(event))

        def _choose_panel(d: Optional[Dict[str, Any]]):
            try:
                if isinstance(d, dict):
                    # If the caller supplied an explicit response panel (direct chat), prefer it
                    panel = d.get('_response_panel') or d.get('response_panel')
                    if panel:
                        return panel
                    prov = d.get('provider') or d.get('provider_name')
                    if prov == 'ollama' and getattr(self, 'ai_panel_ollama', None):
                        return self.ai_panel_ollama
            except Exception:
                pass
            return getattr(self, 'ai_panel', None)

        def _ui_update():
            # Update status bar / status label
            try:
                self._set_status(status)
            except Exception:
                pass

            # Append helpful debug messages to AI panel history when available
            try:
                target = _choose_panel(data)
                try:
                    print(f"[GUIAPI] _ui_update event={event} target={repr(target)}")
                except Exception:
                    pass
                if target and hasattr(target, 'append_message'):
                    if event == 'provider_call_start':
                        target.append_message('status', 'Thinking...')
                    elif event == 'provider_call_end':
                        preview = None
                        if isinstance(data, dict):
                            preview = data.get('preview') or data.get('output_preview') or data.get('preview_text')
                        if preview:
                            target.append_message('status', f'Provider preview: {preview}')
                        else:
                            target.append_message('status', status)
                        # Append verbose debug JSON; prefer AI panel writer to avoid duplicate writes
                        try:
                            dbg = {'ts': time.time(), 'event': event, 'preview': preview, 'data': data}
                            s = json.dumps(dbg, ensure_ascii=False)
                            written = False
                            try:
                                if hasattr(target, 'append_debug'):
                                    try:
                                        written = bool(target.append_debug(s))
                                    except Exception:
                                        written = False
                            except Exception:
                                written = False
                            if not written:
                                try:
                                    _write_debug_line(s)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    elif event == 'responding':
                        final = None
                        if isinstance(data, dict):
                            final = data.get('final_output')
                        if final:
                            target.append_message('assistant', final)
                            try:
                                dbg = {'ts': time.time(), 'event': event, 'final_output': final}
                                s = json.dumps(dbg, ensure_ascii=False)
                                written = False
                                try:
                                    if hasattr(target, 'append_debug'):
                                        try:
                                            written = bool(target.append_debug(s))
                                        except Exception:
                                            written = False
                                except Exception:
                                    written = False
                                if not written:
                                    try:
                                        _write_debug_line(s)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        else:
                            target.append_message('status', status)
                    elif event == 'provider_error':
                        err = data.get('error') if isinstance(data, dict) else str(data)
                        target.append_message('status', f'Provider error: {err}')
                        try:
                            dbg = {'ts': time.time(), 'event': event, 'error': err, 'data': data}
                            s = json.dumps(dbg, ensure_ascii=False)
                            written = False
                            try:
                                if hasattr(target, 'append_debug'):
                                    try:
                                        written = bool(target.append_debug(s))
                                    except Exception:
                                        written = False
                            except Exception:
                                written = False
                            if not written:
                                try:
                                    _write_debug_line(s)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    elif event == 'provider_stream':
                        # Streaming partials from a provider (e.g. Ollama)
                        partial = None
                        if isinstance(data, dict):
                            partial = data.get('partial') or data.get('preview') or data.get('final_output')
                        if partial:
                            try:
                                # Update last assistant message if present, otherwise append
                                if hasattr(target, 'update_last_message'):
                                    target.update_last_message('assistant', partial)
                                else:
                                    target.append_message('assistant', partial)
                                # Update streaming status label when available
                                try:
                                    if isinstance(data, dict) and hasattr(target, 'set_status'):
                                        idx = data.get('index')
                                        total = data.get('total')
                                        if idx is not None and total:
                                            target.set_status(f"Streaming ({idx+1}/{total})")
                                        else:
                                            target.set_status('Streaming...')
                                except Exception:
                                    pass
                            except Exception:
                                try:
                                    target.append_message('assistant', partial)
                                except Exception:
                                    pass
                        else:
                            target.append_message('status', status)
                    elif event == 'done':
                        # Task completed
                        try:
                            target.append_message('status', 'Done')
                        except Exception:
                            pass
                        try:
                            dbg = {'ts': time.time(), 'event': event, 'task_id': data.get('task_id') if isinstance(data, dict) else None}
                            s = json.dumps(dbg, ensure_ascii=False)
                            written = False
                            try:
                                if hasattr(target, 'append_debug'):
                                    written = bool(target.append_debug(s))
                            except Exception:
                                written = False
                            if not written:
                                try:
                                    _write_debug_line(s)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    else:
                        # Generic debug status
                        try:
                            target.append_message('status', status)
                        except Exception:
                            pass
                        try:
                            dbg = {'ts': time.time(), 'event': event, 'data': data}
                            s = json.dumps(dbg, ensure_ascii=False)
                            written = False
                            try:
                                if hasattr(target, 'append_debug'):
                                    written = bool(target.append_debug(s))
                            except Exception:
                                written = False
                            if not written:
                                try:
                                    _write_debug_line(s)
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    # Feedback loop UI event: show chat and diffs, apply diffs
                    if event == 'feedback_iteration':
                        try:
                            chat = None
                            diffs = None
                            if isinstance(data, dict):
                                chat = data.get('chat')
                                diffs = data.get('diffs') or data.get('diff')
                            try:
                                print(f"[GUIAPI] feedback_iteration diffs={type(diffs)}")
                            except Exception:
                                pass
                            # Log feedback iteration details for diagnostics
                            try:
                                dbg = {'ts': time.time(), 'event': 'feedback_iteration', 'chat_preview': (chat or '')[:1000], 'diffs_type': type(diffs).__name__ if diffs is not None else 'None', 'diffs_preview': str(diffs)[:2000]}
                                try:
                                    from bettercopilot.logging import global_debug
                                    global_debug.write(dbg)
                                except Exception:
                                    try:
                                        _write_debug_line(json.dumps(dbg, ensure_ascii=False))
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            if chat and hasattr(target, 'append_message'):
                                try:
                                    target.append_message('assistant', chat)
                                except Exception:
                                    pass

                            # Display diffs in diff viewer and apply to editor
                            if diffs:
                                dlist = diffs if isinstance(diffs, list) else [diffs]
                                try:
                                    if self.diff_viewer:
                                        self.diff_viewer.set_diff(dlist[-1])
                                        # Log that diff was shown in the diff viewer
                                        try:
                                            dbg2 = {'ts': time.time(), 'event': 'diff_shown', 'diff_preview': str(dlist[-1])[:2000]}
                                            try:
                                                from bettercopilot.logging import global_debug
                                                global_debug.write(dbg2)
                                            except Exception:
                                                try:
                                                    _write_debug_line(json.dumps(dbg2, ensure_ascii=False))
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                                if self.editor:
                                    for pd in dlist:
                                        try:
                                            try:
                                                self.editor.apply_diff(diff_text=pd)
                                                applied = True
                                            except Exception:
                                                try:
                                                    self.editor.apply_diff(final_text=pd)
                                                    applied = True
                                                except Exception:
                                                    applied = False
                                            # Log editor apply attempt
                                            try:
                                                dbg3 = {'ts': time.time(), 'event': 'editor_apply_diff', 'applied': bool(applied), 'diff_preview': str(pd)[:2000]}
                                                try:
                                                    from bettercopilot.logging import global_debug
                                                    global_debug.write(dbg3)
                                                except Exception:
                                                    try:
                                                        _write_debug_line(json.dumps(dbg3, ensure_ascii=False))
                                                    except Exception:
                                                        pass
                                            except Exception:
                                                pass
                                        except Exception:
                                            pass
                        except Exception:
                            pass

                    # Feedback prompt UI event: write the temp prompt into the target panel as a user message
                    if event == 'feedback_prompt':
                        try:
                            prompt = None
                            if isinstance(data, dict):
                                prompt = data.get('prompt')
                            if prompt and hasattr(target, 'append_message'):
                                try:
                                    target.append_message('user', prompt)
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except Exception:
                pass

        # Ensure UI updates run on main thread if PySide is present
        try:
            from PySide6.QtCore import QTimer, QCoreApplication

            app = QCoreApplication.instance()
            # If no Qt app instance exists (headless/testing), run update directly.
            if app is None:
                _ui_update()
            else:
                try:
                    thr = app.thread()
                    if hasattr(thr, 'isRunning') and not thr.isRunning():
                        _ui_update()
                    else:
                        QTimer.singleShot(0, _ui_update)
                except Exception:
                    try:
                        QTimer.singleShot(0, _ui_update)
                    except Exception:
                        _ui_update()
        except Exception:
            _ui_update()

    def run_task(self, task: Task, callback=None, error_callback=None):
        # If configured, ensure the task goal instructs the provider to return
        # strict JSON so the UI can parse chat/diff fields reliably.
        try:
            if getattr(self, 'force_json_output', False) and task is not None:
                try:
                    instr = self._json_output_instruction()
                    if isinstance(task.goal, str) and instr not in task.goal:
                        task.goal = instr + "\n\n" + str(task.goal)
                except Exception:
                    pass
        except Exception:
            pass

        worker = Worker(self.orchestrator.run_task, task)

        def _finished_handler(res):
            # Always attempt to update the UI, but ensure the user's
            # callback runs even if UI update fails.
            try:
                self._on_task_finished(res)
            except Exception:
                pass
            if callback:
                try:
                    callback(res)
                except Exception:
                    pass

        def _error_handler(err):
            try:
                self._on_task_error(err)
            except Exception:
                pass
            if error_callback:
                try:
                    error_callback(err)
                except Exception:
                    pass
        # Update status when worker thread starts
        try:
            if hasattr(worker, 'started'):
                try:
                    worker.started.connect(lambda: self._set_status('Thinking...'))
                except Exception:
                    pass
        except Exception:
            pass

        try:
            _connect_signal_to_ui(worker.finished, _finished_handler)
        except Exception:
            try:
                worker.finished.connect(_finished_handler)
            except Exception:
                pass

        try:
            _connect_signal_to_ui(worker.error, _error_handler)
        except Exception:
            try:
                worker.error.connect(_error_handler)
            except Exception:
                pass

        worker.start()
        return worker

    def run_ask(self, goal: str, callback=None, error_callback=None, provider_override: Optional[str] = None, response_panel=None):
        """Run a quick provider call when `direct_chat` is enabled, otherwise
        fall back to the full orchestrator pipeline. Honors `provider_override`
        and routes UI updates to `response_panel` when provided.
        """
        try:
            print(f"[GUIAPI] run_ask received goal (len={len(goal) if goal else 0}) direct_chat={getattr(self,'direct_chat',False)} provider_override={provider_override}")

            if getattr(self, 'direct_chat', False):
                provider_name = None
                try:
                    provs = getattr(self.orchestrator, 'providers', {}) or {}
                    # honor explicit override when possible
                    if provider_override:
                        if provider_override in provs:
                            provider_name = provider_override
                        else:
                            matches = [k for k in provs.keys() if k.startswith(provider_override)]
                            if matches:
                                provider_name = matches[0]
                    # prefer OpenRouter if no override
                    if provider_name is None:
                        if 'openrouter' in provs:
                            provider_name = 'openrouter'
                        elif 'ollama' in provs:
                            provider_name = 'ollama'
                        else:
                            provider_name = next(iter(provs.keys())) if provs else None
                except Exception:
                    provider_name = None

                print(f"[GUIAPI] direct_chat provider selected: {provider_name}")

                if provider_name and hasattr(self.orchestrator, 'providers'):
                    provider = self.orchestrator.providers.get(provider_name)

                    # Build a chat-like message list from the provided panel history if available
                    messages = []
                    try:
                        hist_panel = response_panel or self.ai_panel
                        if hist_panel and hasattr(hist_panel, 'get_history'):
                            for entry in hist_panel.get_history():
                                if not isinstance(entry, dict):
                                    continue
                                role = entry.get('role')
                                text = entry.get('text')
                                if role == 'user':
                                    messages.append({'role': 'user', 'content': text})
                                elif role == 'assistant':
                                    messages.append({'role': 'assistant', 'content': text})
                                else:
                                    messages.append({'role': 'system', 'content': text})
                    except Exception:
                        messages = []

                    # Optionally enforce JSON-only responses by inserting a
                    # single system instruction before the user message.
                    try:
                        if getattr(self, 'force_json_output', False):
                            try:
                                instr = self._json_output_instruction()
                                # Insert as system message at the front so it has
                                # high precedence.
                                messages.insert(0, {'role': 'system', 'content': instr})
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # Detect leading slash-commands in the user prompt portion
                    # of `goal`. Support the case where `goal` wraps the user
                    # prompt (e.g. MainWindow._make_goal_with_editor).
                    chat_only = False
                    feedback_iters = 0
                    try:
                        g = (goal or '')
                        prefix = ''
                        user_prompt = g
                        if 'User prompt:' in g:
                            parts = g.split('User prompt:', 1)
                            prefix = parts[0]
                            user_prompt = parts[1].strip()

                        # Parse commands from the extracted user prompt
                        if user_prompt.startswith('/chat'):
                            chat_only = True
                            user_prompt = user_prompt[len('/chat'):].lstrip()

                        if user_prompt.startswith('/feedback'):
                            rest = user_prompt[len('/feedback'):]
                            if rest.startswith('='):
                                try:
                                    feedback_iters = int(rest[1:].split()[0])
                                except Exception:
                                    feedback_iters = 3
                                parts = rest[1:].lstrip().split(None, 1)
                                if len(parts) > 1:
                                    user_prompt = parts[1]
                                else:
                                    user_prompt = ''
                            else:
                                feedback_iters = 3
                                user_prompt = rest.lstrip()

                        # Reconstruct user_content preserving any editor prefix
                        if prefix:
                            user_content = prefix + 'User prompt:\n' + (user_prompt or '')
                        else:
                            user_content = user_prompt
                    except Exception:
                        user_content = goal

                    # If /chat was requested, request no diffs from provider.
                    try:
                        if chat_only:
                            messages.insert(0, {'role': 'system', 'content': 'Respond with JSON where the "diff" or "diffs" fields are empty (empty string or empty array).'})
                    except Exception:
                        pass

                    # Append the new user message and call provider in a worker
                    messages.append({'role': 'user', 'content': user_content or goal})

                    # Capture editor content now on the main thread so the
                    # worker thread does not call GUI APIs.
                    try:
                        captured_editor_text = None
                        if self.editor and hasattr(self.editor, 'get_text'):
                            captured_editor_text = self.editor.get_text()
                    except Exception:
                        captured_editor_text = None

                    def _call_provider():
                        try:
                            try:
                                print(f"[GUIAPI] provider.generate START provider={provider_name} messages_len={len(messages)}")
                            except Exception:
                                pass
                            # Emit a concise provider-call start event for debug/observability
                            try:
                                from bettercopilot.logging import global_debug
                                try:
                                    global_debug.write({'ts': time.time(), 'event': 'provider_call_start', 'provider': provider_name, 'messages_len': len(messages), 'messages_preview': str(messages)[:2000]})
                                except Exception:
                                    pass
                            except Exception:
                                pass
                            # Wrap the provider progress callback so we can route
                            # streaming events to the UI panel that initiated the call.
                            def _progress_wrapper(event, d=None):
                                try:
                                    if isinstance(d, dict):
                                        dd = dict(d)
                                    else:
                                        dd = {'_raw': d}
                                    # Attach the response panel so _handle_progress
                                    # can route updates to it.
                                    dd['_response_panel'] = response_panel or hist_panel
                                except Exception:
                                    dd = {'_response_panel': response_panel or hist_panel}
                                try:
                                    self._handle_progress(event, dd)
                                except Exception:
                                    pass

                            out = provider.generate(messages, progress_callback=_progress_wrapper)
                            try:
                                print(f"[GUIAPI] provider.generate RETURN provider={provider_name} type={type(out)}")
                            except Exception:
                                pass

                            # Prefer the provider's `text` field when available; otherwise
                            # fall back to stringifying the entire response object.
                            text = ''
                            try:
                                if isinstance(out, dict):
                                    text = out.get('text') or (out.get('raw') or {}).get('output') or ''
                                    # If provider returned no text, write raw response to debug
                                    try:
                                        if not text:
                                            dbg = {'ts': time.time(), 'event': 'provider_raw', 'provider': provider_name, 'raw': out}
                                            s = json.dumps(dbg, ensure_ascii=False)
                                            try:
                                                _write_debug_line(s)
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                                else:
                                    text = str(out)
                            except Exception:
                                try:
                                    text = str(out)
                                except Exception:
                                    text = ''

                            # Always write a concise provider return preview for diagnostics
                            try:
                                try:
                                    preview_text = text if isinstance(text, str) else str(text)
                                except Exception:
                                    preview_text = ''
                                dbg2 = {'ts': time.time(), 'event': 'provider_return', 'provider': provider_name, 'text_preview': preview_text[:1000], 'raw_preview': str(out)[:2000]}
                                s2 = json.dumps(dbg2, ensure_ascii=False)
                                try:
                                    _write_debug_line(s2)
                                except Exception:
                                    pass
                                try:
                                    # notify UI via progress handler so UI-thread callbacks
                                    # perform any panel updates rather than the worker thread.
                                    self._handle_progress('provider_call_end', {'preview': preview_text, '_response_panel': response_panel, 'data': out})
                                except Exception:
                                    pass
                            except Exception:
                                pass

                            # Attempt to detect and propagate any diffs/patches returned
                            # by the provider. Providers may return a `diffs` list,
                            # or a single patch under keys like `patch`, `diff`, or
                            # `patch_text`. If none are present, heuristically detect
                            # a unified-diff in the returned text.
                            diffs = []
                            try:
                                if isinstance(out, dict):
                                    # explicit diffs list
                                    cand = out.get('diffs')
                                    if isinstance(cand, list) and cand:
                                        diffs = cand
                                    else:
                                        patch_cand = out.get('patch') or out.get('diff') or out.get('patch_text')
                                        if patch_cand:
                                            if isinstance(patch_cand, list):
                                                diffs = patch_cand
                                            else:
                                                diffs = [patch_cand]
                                # Heuristic: inspect provider text or raw output for unified-diff markers
                                if not diffs:
                                    try:
                                        probe = ''
                                        if isinstance(out, dict):
                                            probe = out.get('text') or ''
                                        if not probe:
                                            probe = text or ''
                                        rt = str(probe or '')
                                        if rt.strip().startswith('diff ') or ('--- ' in rt and '+++ ' in rt) or rt.strip().startswith('@@ '):
                                            diffs = [rt]
                                    except Exception:
                                        pass
                            except Exception:
                                diffs = []

                            result = {'task_id': str(uuid.uuid4()), 'final_text': text, 'diffs': diffs, 'logs': [{'provider': provider_name, 'output_preview': text}], 'raw': out}
                            try:
                                print(f"[GUIAPI] provider returned text len={len(text)}")
                            except Exception:
                                pass
                            # If feedback loop requested, forward assistant output
                            # to other providers to critique/improve, simulating
                            # application of diffs to the editor between iterations.
                            try:
                                try:
                                    print(f"[GUIAPI] feedback_iters={feedback_iters}")
                                except Exception:
                                    pass
                                if feedback_iters and isinstance(feedback_iters, int) and feedback_iters > 0:
                                    # Try to import unified diff applier
                                    try:
                                        from .editor import _apply_unified_diff
                                    except Exception:
                                        _apply_unified_diff = None

                                    # Use captured editor content grabbed on the main thread
                                    current_text = captured_editor_text

                                    prev_chat = text
                                    prev_diffs = diffs
                                    cur_provider = provider_name
                                    # iterate, alternating to next available provider (cap iterations at 10)
                                    try:
                                        max_iters = min(int(feedback_iters), 10)
                                    except Exception:
                                        max_iters = 3
                                    for it in range(max_iters):
                                        # pick next provider different from cur_provider
                                        try:
                                            prov_keys = list((getattr(self.orchestrator, 'providers', {}) or {}).keys())
                                        except Exception:
                                            prov_keys = []
                                        next_prov = None
                                        for k in prov_keys:
                                            if k != cur_provider:
                                                next_prov = k
                                                break
                                        if not next_prov:
                                            break

                                            try:
                                                print(f"[GUIAPI] feedback loop iter={it} cur_provider={cur_provider} next_prov={next_prov}")
                                            except Exception:
                                                pass

                                        # Build simulated editor content after applying prev_diffs
                                        simulated_editor = current_text
                                        try:
                                            if _apply_unified_diff and simulated_editor is not None and prev_diffs:
                                                # prev_diffs may be list or single string
                                                try:
                                                    if isinstance(prev_diffs, list):
                                                        for pd in prev_diffs:
                                                            simulated_editor = _apply_unified_diff(simulated_editor, pd)
                                                    else:
                                                        simulated_editor = _apply_unified_diff(simulated_editor, str(prev_diffs))
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass

                                        # Build the tempPrompt that will be shown and sent to the next provider
                                        tempPrompt = (
                                            "Review, fix, and improve the current editor contents. The most recent work I did is as follows:\n\n"
                                            + (prev_chat or '')
                                            + "\n\nApply improvements to the editor content below and respond with a single JSON object containing keys 'chat' (a short human-readable summary) and 'diff' or 'diffs' (one or more unified-diff strings). "
                                            "Place ALL file-edit content exclusively in the 'diff'/'diffs' fields; do NOT include file edits inside 'chat'. Do not include any text outside the JSON object.\n\n"
                                            "Editor (simulated after applying previous edits):\n" + (simulated_editor or '')
                                        )

                                        # Prepare messages for next provider using tempPrompt
                                        next_msgs = []
                                        try:
                                            if getattr(self, 'force_json_output', False):
                                                next_msgs.append({'role': 'system', 'content': self._json_output_instruction()})
                                        except Exception:
                                            pass
                                        next_msgs.append({'role': 'system', 'content': 'Review and improve the previous assistant output; emit JSON with chat and diff(s).'})
                                        next_msgs.append({'role': 'user', 'content': tempPrompt})

                                        try:
                                            next_provider = self.orchestrator.providers.get(next_prov)
                                            try:
                                                print(f"[GUIAPI] next_provider resolved: {bool(next_provider)}")
                                            except Exception:
                                                pass
                                            if not next_provider:
                                                break
                                        except Exception:
                                            break

                                        # Show the temp prompt in the next provider's AI panel (UI thread)
                                        # Resolve the UI panel for the next provider. Prefer a
                                        # provider-specific attribute named `ai_panel_<prov>`,
                                        # then the Ollama panel (if provider name contains
                                        # 'ollama'), otherwise fall back to the default panel.
                                        try:
                                            next_panel = None
                                            if next_prov:
                                                try:
                                                    next_panel = getattr(self, f'ai_panel_{next_prov}', None)
                                                except Exception:
                                                    next_panel = None
                                            if not next_panel:
                                                try:
                                                    if next_prov and 'ollama' in next_prov and getattr(self, 'ai_panel_ollama', None):
                                                        next_panel = self.ai_panel_ollama
                                                except Exception:
                                                    next_panel = None
                                            if not next_panel:
                                                next_panel = self.ai_panel
                                            try:
                                                self._handle_progress('feedback_prompt', {'prompt': tempPrompt, '_response_panel': next_panel})
                                            except Exception:
                                                pass
                                        except Exception:
                                            pass

                                        # call provider.generate synchronously in worker thread
                                        try:
                                            # Create a progress wrapper bound to the next panel
                                            def _progress_wrapper_for_next(event, d=None):
                                                try:
                                                    if isinstance(d, dict):
                                                        dd = dict(d)
                                                    else:
                                                        dd = {'_raw': d}
                                                    dd['_response_panel'] = next_panel
                                                except Exception:
                                                    dd = {'_response_panel': next_panel}
                                                try:
                                                    self._handle_progress(event, dd)
                                                except Exception:
                                                    pass

                                            nxt_out = next_provider.generate(next_msgs, progress_callback=_progress_wrapper_for_next)
                                            try:
                                                print(f"[GUIAPI] next_provider.generate RETURN type={type(nxt_out)}")
                                            except Exception:
                                                pass
                                        except Exception:
                                            break

                                        # parse returned text similarly
                                            try:
                                                nxt_text = ''
                                                if isinstance(nxt_out, dict):
                                                    nxt_text = nxt_out.get('text') or (nxt_out.get('raw') or {}).get('output') or ''
                                                else:
                                                    nxt_text = str(nxt_out)
                                                try:
                                                    print(f"[GUIAPI] nxt_text len={len(nxt_text) if nxt_text else 0}")
                                                except Exception:
                                                    pass
                                            except Exception:
                                                nxt_text = ''

                                            # extract json payload if present
                                            try:
                                                pj = _extract_json_from_string(nxt_text) if isinstance(nxt_text, str) else None
                                            except Exception:
                                                pj = None
                                            try:
                                                try:
                                                    print(f"[GUIAPI] parsed pj: {repr(pj)[:200]}")
                                                except Exception:
                                                    pass
                                            except Exception:
                                                pj = None

                                            # update prev_chat and prev_diffs for next iter and notify UI
                                            try:
                                                if isinstance(pj, dict):
                                                    prev_chat = pj.get('chat') or prev_chat
                                                    if 'diff' in pj:
                                                        prev_diffs = pj.get('diff')
                                                    elif 'diffs' in pj:
                                                        prev_diffs = pj.get('diffs')
                                                    # If chat contains a patch, move it into diffs when configured
                                                    try:
                                                        if getattr(self, 'enforce_diff_in_json', False) and isinstance(prev_chat, str) and _looks_like_unified_diff(prev_chat) and not prev_diffs:
                                                            prev_diffs = prev_chat
                                                            prev_chat = 'Provided patch moved to diff field.'
                                                    except Exception:
                                                        pass
                                                    # Notify UI: show chat and diffs and apply them in the next provider's panel
                                                    try:
                                                        self._handle_progress('feedback_iteration', {'chat': prev_chat, 'diffs': prev_diffs, '_response_panel': next_panel})
                                                        try:
                                                            print('[GUIAPI] called _handle_progress feedback_iteration (dict)')
                                                        except Exception:
                                                            pass
                                                    except Exception:
                                                        pass
                                                else:
                                                    prev_chat = nxt_text or prev_chat
                                                    try:
                                                        self._handle_progress('feedback_iteration', {'chat': prev_chat, 'diffs': None, '_response_panel': next_panel})
                                                        try:
                                                            print('[GUIAPI] called _handle_progress feedback_iteration (text)')
                                                        except Exception:
                                                            pass
                                                    except Exception:
                                                        pass
                                            except Exception:
                                                pass

                                            # rotate provider
                                            cur_provider = next_prov
                                        except Exception:
                                            break

                                    # after feedback loop, set final aggregated values
                                    try:
                                        text = prev_chat or text
                                        diffs = prev_diffs or diffs
                                        result['final_text'] = text
                                        result['diffs'] = diffs
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                            return result
                        except Exception as e:
                            try:
                                import traceback
                                print(f"[GUIAPI] provider.generate EXCEPTION provider={provider_name}: {e}")
                                traceback.print_exc()
                            except Exception:
                                pass
                            raise

                    # Run provider call in worker so it doesn't block UI
                    print(f"[GUIAPI] starting provider worker for {provider_name}")
                    worker = Worker(_call_provider)

                    def _finished_handler(res):
                        try:
                            # update UI first (route to response panel when provided)
                            self._on_task_finished(res, origin='direct', panel=response_panel)
                        except Exception:
                            pass
                        finally:
                            # remove worker reference so it can be GC'ed
                            try:
                                if hasattr(self, '_workers') and worker in self._workers:
                                    self._workers.remove(worker)
                            except Exception:
                                pass
                        if callback:
                            try:
                                callback(res)
                            except Exception:
                                pass

                    def _error_handler(err):
                        try:
                            self._on_task_error(err)
                        except Exception:
                            pass
                        finally:
                            try:
                                if hasattr(self, '_workers') and worker in self._workers:
                                    self._workers.remove(worker)
                            except Exception:
                                pass
                        if error_callback:
                            try:
                                error_callback(err)
                            except Exception:
                                pass

                    try:
                        _connect_signal_to_ui(worker.finished, _finished_handler)
                    except Exception:
                        try:
                            worker.finished.connect(_finished_handler)
                        except Exception:
                            pass
                    try:
                        _connect_signal_to_ui(worker.error, _error_handler)
                    except Exception:
                        try:
                            worker.error.connect(_error_handler)
                        except Exception:
                            pass

                    # Update status and start
                    try:
                        self._set_status('Prompt sent')
                    except Exception:
                        pass
                    try:
                        if hasattr(worker, 'started'):
                            try:
                                worker.started.connect(lambda: self._set_status('Thinking...'))
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # Keep a reference to the worker so it isn't GC'd while running
                    try:
                        if not hasattr(self, '_workers'):
                            self._workers = []
                        self._workers.append(worker)
                    except Exception:
                        pass

                    try:
                        worker.start()
                        print(f"[GUIAPI] worker started for {provider_name}")
                    except Exception as e:
                        print(f"[GUIAPI] worker start failed: {e}")
                        # cleanup reference
                        try:
                            if hasattr(self, '_workers') and worker in self._workers:
                                self._workers.remove(worker)
                        except Exception:
                            pass
                        raise
                    return worker
        except Exception:
            pass

        # Fallback to orchestrator pipeline
        print("[GUIAPI] falling back to orchestrator pipeline")
        t = Task(id=str(uuid.uuid4()), goal=goal)
        # Respect provider_override when provided, otherwise prefer OpenRouter.
        try:
            provs = getattr(self.orchestrator, 'providers', {}) or {}
            assigned = None
            if provider_override:
                if provider_override in provs:
                    assigned = provider_override
                else:
                    matches = [k for k in provs.keys() if k.startswith(provider_override)]
                    if matches:
                        assigned = matches[0]
            if not assigned and 'openrouter' in provs:
                assigned = 'openrouter'
            if assigned:
                t.provider = assigned
        except Exception:
            pass
        # Indicate prompt was sent
        try:
            self._set_status('Prompt sent')
        except Exception:
            pass
        return self.run_task(t, callback=callback, error_callback=error_callback)

    def run_fix(self, path: str, callback=None, error_callback=None):
        t = Task(id=str(uuid.uuid4()), goal=f"Fix file {path}", files=[path])
        return self.run_task(t, callback=callback, error_callback=error_callback)

    def run_rom_analysis(self, path: str, callback=None, error_callback=None):
        t = Task(id=str(uuid.uuid4()), goal=f"Analyze ROM {path}", tools=['fusion_inspect'])
        return self.run_task(t, callback=callback, error_callback=error_callback)

    def apply_patch(self, patch: Dict[str, Any]):
        # Patch is expected to be a dict like {'patch': '<unified diff>', 'final_text': '...'}
        if not self.editor:
            return

        text = patch.get('patch') if isinstance(patch, dict) else patch
        final = patch.get('final_text') if isinstance(patch, dict) else None

        # preserve original content so we can revert if user cancels
        try:
            orig_text = self.editor.get_text()
        except Exception:
            orig_text = None

        try:
            # apply the change to the editor first
            self.editor.apply_diff(diff_text=text, final_text=final)

            # Decide whether to save automatically or prompt the user
            do_save = False
            if getattr(self, 'autosave', False):
                do_save = True
            else:
                # Try to prompt using PySide6 if available; otherwise do not save
                try:
                    from PySide6.QtWidgets import QMessageBox, QFileDialog
                    PYSIDE = True
                except Exception:
                    PYSIDE = False

                if PYSIDE:
                    try:
                        resp = QMessageBox.question(None, 'Save Patch', 'Save changes to file?', QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                        if resp == QMessageBox.Yes:
                            do_save = True
                        elif resp == QMessageBox.Cancel:
                            # revert changes
                            if orig_text is not None:
                                try:
                                    self.editor.set_text(orig_text)
                                except Exception:
                                    pass
                            if self.status_bar:
                                self.status_bar.set_message('Patch cancelled')
                            return
                        else:
                            do_save = False
                    except Exception:
                        do_save = False

            if do_save:
                try:
                    saved = False
                    try:
                        saved = self.editor.save_file()
                    except TypeError:
                        # some implementations may require a path arg
                        saved = False

                    if not saved and PYSIDE:
                        try:
                            fname, _ = QFileDialog.getSaveFileName(None, 'Save file', '.', 'All Files (*)')
                            if fname:
                                self.editor.save_file(fname)
                                saved = True
                        except Exception:
                            saved = False

                    if self.status_bar:
                        self.status_bar.set_message('Patch applied and saved' if saved else 'Patch applied (save failed)')
                except Exception:
                    if self.status_bar:
                        self.status_bar.set_message('Applied patch but failed to save')
            else:
                if self.status_bar:
                    self.status_bar.set_message('Patch applied (not saved)')

        except Exception:
            # Restore original text on failure
            try:
                if orig_text is not None:
                    self.editor.set_text(orig_text)
            except Exception:
                pass
            if self.status_bar:
                self.status_bar.set_message('Failed to apply patch')

    def set_autosave(self, enabled: bool):
        self.autosave = bool(enabled)
        if self.status_bar:
            try:
                self.status_bar.set_message(f'Autosave: {"on" if self.autosave else "off"}')
            except Exception:
                pass

    def get_autosave(self) -> bool:
        return bool(self.autosave)

