"""Thin GUI -> Orchestrator API wrapper.

This module provides convenience functions used by the GUI to run tasks
via the orchestrator without blocking the GUI thread.
"""
from typing import Optional, Dict, Any
import json
import time
from pathlib import Path
from .worker import Worker
from bettercopilot.orchestrator.task import Task
from bettercopilot.orchestrator.orchestrator import Orchestrator
from bettercopilot.providers.ollama_local import OllamaLocalProvider
from bettercopilot.mcp.registry import MCPRegistry
import uuid
import os

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

    # Add Ollama HTTP provider only if an explicit OLLAMA_URL/OLLAMA_HOST is configured
    try:
        ollama_url = os.getenv('OLLAMA_URL') or os.getenv('OLLAMA_HOST')
        if ollama_url and OllamaHTTPProvider is not None:
            try:
                providers['ollama'] = OllamaHTTPProvider(api_url=ollama_url)
            except Exception:
                pass
    except Exception:
        pass

    # Always include the simulated local provider as a fallback if no HTTP Ollama
    if 'ollama' not in providers and 'ollama_local' not in providers:
        providers['ollama_local'] = OllamaLocalProvider()

    registry = MCPRegistry()
    return Orchestrator(providers, registry, progress_callback=progress_callback)


def _write_debug_line(s: str, max_bytes: int = 5 * 1024 * 1024) -> bool:
    """Write a debug JSON line to disk using several candidate locations.

    Returns True if write succeeded.
    """
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


def run_task(task: Task, callback=None, error_callback=None) -> Worker:
    orch = _make_orchestrator()
    worker = Worker(orch.run_task, task)
    # Connect handlers robustly so user callbacks always run even if
    # other UI-update logic raises an exception.
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
        worker.finished.connect(_finished_handler)
    except Exception:
        try:
            worker.finished.connect(_finished_handler)
        except Exception:
            pass

    try:
        worker.error.connect(_error_handler)
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
        worker.finished.connect(_finished_handler)
    except Exception:
        try:
            worker.finished.connect(_finished_handler)
        except Exception:
            pass

    try:
        worker.error.connect(_error_handler)
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
        self.direct_chat = False

    def bind_frontend(self, frontend):
        # frontend expected to be MainWindow or HeadlessMainWindow
        self.editor = getattr(frontend, 'editor', None)
        self.file_tree = getattr(frontend, 'file_tree', None)
        self.ai_panel = getattr(frontend, 'ai_panel', None)
        self.diff_viewer = getattr(frontend, 'diff_viewer', None)
        self.status_bar = getattr(frontend, 'status_bar', None)
        # Report which providers were loaded so the user can verify configuration
        try:
            provs = []
            if hasattr(self, 'orchestrator') and getattr(self.orchestrator, 'providers', None):
                provs = list(self.orchestrator.providers.keys())
            if self.ai_panel and provs:
                try:
                    self.ai_panel.append_message('status', f"Providers: {', '.join(provs)}")
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
            except Exception:
                if self.status_bar:
                    self.status_bar.set_message(f'Failed to open {path}')

    def _on_task_finished(self, result: Dict[str, Any], origin: str = 'task'):
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
        diffs = result.get('diffs') or []
        logs = result.get('logs') or []

        if self.ai_panel and final:
            # Ensure UI updates are resilient; schedule via Qt event loop if needed
            try:
                self.ai_panel.append_message('assistant', final)
                try:
                    print(f"[GUIAPI] appended assistant message to ai_panel (len={len(final)})")
                except Exception:
                    pass
            except Exception:
                try:
                    # best-effort: call via QTimer if available
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self.ai_panel.append_message('assistant', final))
                except Exception:
                    pass

        if self.diff_viewer and diffs:
            # display latest diff
            self.diff_viewer.set_diff(diffs[-1])

        if self.editor and final and not diffs:
            # if there's a final_text and no diffs, update editor content
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

        def _ui_update():
            # Update status bar / status label
            try:
                self._set_status(status)
            except Exception:
                pass

            # Append helpful debug messages to AI panel history when available
            try:
                if self.ai_panel and hasattr(self.ai_panel, 'append_message'):
                    if event == 'provider_call_start':
                        self.ai_panel.append_message('status', 'Thinking...')
                    elif event == 'provider_call_end':
                        preview = None
                        if isinstance(data, dict):
                            preview = data.get('preview') or data.get('output_preview') or data.get('preview_text')
                        if preview:
                            self.ai_panel.append_message('status', f'Provider preview: {preview}')
                        else:
                            self.ai_panel.append_message('status', status)
                        # Append verbose debug JSON; prefer AI panel writer to avoid duplicate writes
                        try:
                            dbg = {'ts': time.time(), 'event': event, 'preview': preview, 'data': data}
                            s = json.dumps(dbg, ensure_ascii=False)
                            written = False
                            try:
                                if hasattr(self.ai_panel, 'append_debug'):
                                    try:
                                        written = bool(self.ai_panel.append_debug(s))
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
                            self.ai_panel.append_message('assistant', final)
                            try:
                                dbg = {'ts': time.time(), 'event': event, 'final_output': final}
                                s = json.dumps(dbg, ensure_ascii=False)
                                written = False
                                try:
                                    if hasattr(self.ai_panel, 'append_debug'):
                                        try:
                                            written = bool(self.ai_panel.append_debug(s))
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
                            self.ai_panel.append_message('status', status)
                    elif event == 'provider_error':
                        err = data.get('error') if isinstance(data, dict) else str(data)
                        self.ai_panel.append_message('status', f'Provider error: {err}')
                        try:
                            dbg = {'ts': time.time(), 'event': event, 'error': err, 'data': data}
                            s = json.dumps(dbg, ensure_ascii=False)
                            written = False
                            try:
                                if hasattr(self.ai_panel, 'append_debug'):
                                    try:
                                        written = bool(self.ai_panel.append_debug(s))
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
                    elif event == 'done':
                        self.ai_panel.append_message('status', 'Done')
                        try:
                            dbg = {'ts': time.time(), 'event': event, 'task_id': data.get('task_id') if isinstance(data, dict) else None}
                            s = json.dumps(dbg, ensure_ascii=False)
                            written = False
                            try:
                                if hasattr(self.ai_panel, 'append_debug'):
                                    try:
                                        written = bool(self.ai_panel.append_debug(s))
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
                        # Generic debug status
                        self.ai_panel.append_message('status', status)
                        try:
                            dbg = {'ts': time.time(), 'event': event, 'data': data}
                            s = json.dumps(dbg, ensure_ascii=False)
                            written = False
                            try:
                                if hasattr(self.ai_panel, 'append_debug'):
                                    try:
                                        written = bool(self.ai_panel.append_debug(s))
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
            except Exception:
                pass

        # Ensure UI updates run on main thread if PySide is present
        try:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, _ui_update)
        except Exception:
            _ui_update()

    def run_task(self, task: Task, callback=None, error_callback=None):
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
            worker.finished.connect(_finished_handler)
        except Exception:
            try:
                worker.finished.connect(_finished_handler)
            except Exception:
                pass

        try:
            worker.error.connect(_error_handler)
        except Exception:
            try:
                worker.error.connect(_error_handler)
            except Exception:
                pass

        worker.start()
        return worker

    def run_ask(self, goal: str, callback=None, error_callback=None):
        # Fast-path: if direct_chat mode enabled and a provider is available,
        # call the provider.generate directly and return its output quickly.
        try:
            print(f"[GUIAPI] run_ask received goal (len={len(goal) if goal else 0}) direct_chat={getattr(self,'direct_chat',False)}")
            if getattr(self, 'direct_chat', False):
                provider_name = None
                try:
                    if hasattr(self.orchestrator, 'providers') and self.orchestrator.providers:
                        # prefer openrouter if present
                        if 'openrouter' in self.orchestrator.providers:
                            provider_name = 'openrouter'
                        elif 'ollama' in self.orchestrator.providers:
                            provider_name = 'ollama'
                        else:
                            provider_name = next(iter(self.orchestrator.providers.keys()))
                except Exception:
                    provider_name = None
                print(f"[GUIAPI] direct_chat provider selected: {provider_name}")
                if provider_name and hasattr(self.orchestrator, 'providers'):
                    provider = self.orchestrator.providers.get(provider_name)

                    # Build a chat-like message list from the AI panel history if available
                    messages = []
                    try:
                        if self.ai_panel and hasattr(self.ai_panel, 'get_history'):
                            for entry in self.ai_panel.get_history():
                                if not isinstance(entry, dict):
                                    continue
                                role = entry.get('role')
                                text = entry.get('text')
                                if role == 'user':
                                    messages.append({'role': 'user', 'content': text})
                                elif role == 'assistant':
                                    messages.append({'role': 'assistant', 'content': text})
                                else:
                                    # treat status/debug as system/assistant hints
                                    messages.append({'role': 'assistant', 'content': text})
                        else:
                            messages = []
                    except Exception:
                        messages = []

                    # Append the new user message and call provider in a worker
                    messages.append({'role': 'user', 'content': goal})

                    def _call_provider():
                        try:
                            try:
                                print(f"[GUIAPI] provider.generate START provider={provider_name} messages_len={len(messages)}")
                            except Exception:
                                pass
                            out = provider.generate(messages)
                            try:
                                print(f"[GUIAPI] provider.generate RETURN provider={provider_name} type={type(out)}")
                            except Exception:
                                pass
                            if isinstance(out, dict):
                                text = out.get('text') or (out.get('raw') or {}).get('output') or ''
                            else:
                                text = str(out)
                            result = {'task_id': str(uuid.uuid4()), 'final_text': text, 'logs': [{'provider': provider_name, 'output_preview': text}], 'raw': out}
                            try:
                                print(f"[GUIAPI] provider returned text len={len(text)}")
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
                            # update UI first
                            self._on_task_finished(res, origin='direct')
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
                        worker.finished.connect(_finished_handler)
                    except Exception:
                        try:
                            worker.finished.connect(_finished_handler)
                        except Exception:
                            pass
                    try:
                        worker.error.connect(_error_handler)
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
        # If this orchestrator has OpenRouter configured, use it by default.
        try:
            if hasattr(self.orchestrator, 'providers') and 'openrouter' in self.orchestrator.providers:
                t.provider = 'openrouter'
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

