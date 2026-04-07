"""Thin GUI -> Orchestrator API wrapper.

This module provides convenience functions used by the GUI to run tasks
via the orchestrator without blocking the GUI thread.
"""
from typing import Optional, Dict, Any
from .worker import Worker
from bettercopilot.orchestrator.task import Task
from bettercopilot.orchestrator.orchestrator import Orchestrator
from bettercopilot.providers.ollama_local import OllamaLocalProvider
from bettercopilot.mcp.registry import MCPRegistry
import uuid


def _make_orchestrator():
    providers = {"ollama_local": OllamaLocalProvider()}
    registry = MCPRegistry()
    return Orchestrator(providers, registry)


def run_task(task: Task, callback=None, error_callback=None) -> Worker:
    orch = _make_orchestrator()
    worker = Worker(orch.run_task, task)
    if callback:
        worker.finished.connect(callback) if hasattr(worker, 'finished') else worker.finished.connect(callback)
    if error_callback:
        worker.error.connect(error_callback)
    worker.start()
    return worker


def run_ask(goal: str, callback=None, error_callback=None) -> Worker:
    t = Task(id=str(uuid.uuid4()), goal=goal, provider='ollama_local')
    return run_task(t, callback=callback, error_callback=error_callback)


def run_fix(path: str, callback=None, error_callback=None) -> Worker:
    t = Task(id=str(uuid.uuid4()), goal=f"Fix file {path}", provider='ollama_local')
    return run_task(t, callback=callback, error_callback=error_callback)


def run_rom_analysis(path: str, callback=None, error_callback=None) -> Worker:
    t = Task(id=str(uuid.uuid4()), goal=f"Analyze ROM {path}", provider='ollama_local', tools=['fusion_inspect'])
    return run_task(t, callback=callback, error_callback=error_callback)


class GUIAPI:
    """High-level API object the GUI can bind to.

    Methods are designed to be simple and to update bound frontend panels
    when worker results arrive. Bind the frontend via `bind_frontend(mainwin)`
    where `mainwin` exposes `editor`, `file_tree`, `ai_panel`, `diff_viewer`,
    and `status_bar` attributes.
    """

    def __init__(self, orchestrator: Optional[Orchestrator] = None):
        self.orchestrator = orchestrator or _make_orchestrator()
        self.editor = None
        self.file_tree = None
        self.ai_panel = None
        self.diff_viewer = None
        self.status_bar = None

    def bind_frontend(self, frontend):
        # frontend expected to be MainWindow or HeadlessMainWindow
        self.editor = getattr(frontend, 'editor', None)
        self.file_tree = getattr(frontend, 'file_tree', None)
        self.ai_panel = getattr(frontend, 'ai_panel', None)
        self.diff_viewer = getattr(frontend, 'diff_viewer', None)
        self.status_bar = getattr(frontend, 'status_bar', None)

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
        final = result.get('final_text')
        diffs = result.get('diffs') or []
        logs = result.get('logs') or []

        if self.ai_panel and final:
            self.ai_panel.append_message('assistant', final)

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

    def run_task(self, task: Task, callback=None, error_callback=None):
        worker = Worker(self.orchestrator.run_task, task)
        # wire UI update
        worker.finished.connect(lambda res: (self._on_task_finished(res), callback(res) if callback else None)) if hasattr(worker, 'finished') else worker.finished.connect(lambda res: (self._on_task_finished(res), callback(res) if callback else None))
        worker.error.connect(lambda e: (self._on_task_error(e), error_callback(e) if error_callback else None))
        worker.start()
        return worker

    def run_ask(self, goal: str, callback=None, error_callback=None):
        t = Task(id=str(uuid.uuid4()), goal=goal, provider='ollama_local')
        return self.run_task(t, callback=callback, error_callback=error_callback)

    def run_fix(self, path: str, callback=None, error_callback=None):
        t = Task(id=str(uuid.uuid4()), goal=f"Fix file {path}", provider='ollama_local', files=[path])
        return self.run_task(t, callback=callback, error_callback=error_callback)

    def run_rom_analysis(self, path: str, callback=None, error_callback=None):
        t = Task(id=str(uuid.uuid4()), goal=f"Analyze ROM {path}", provider='ollama_local', tools=['fusion_inspect'])
        return self.run_task(t, callback=callback, error_callback=error_callback)

    def apply_patch(self, patch: Dict[str, Any]):
        # Patch is expected to be a dict like {'patch': '<unified diff>'}
        if not self.editor:
            return
        text = patch.get('patch') if isinstance(patch, dict) else patch
        try:
            # For now, if the patch contains a final_text key, prefer it
            final = patch.get('final_text') if isinstance(patch, dict) else None
            self.editor.apply_diff(diff_text=text, final_text=final)
            if self.status_bar:
                self.status_bar.set_message('Patch applied')
        except Exception:
            if self.status_bar:
                self.status_bar.set_message('Failed to apply patch')

