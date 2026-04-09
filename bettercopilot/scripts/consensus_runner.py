#!/usr/bin/env python3
"""Run a headless consensus feedback loop for a single todo/task.

This script is intended to be invoked in a fresh process per task so
that each run is isolated (no shared state or lingering Qt app).
"""
import argparse
import time
import json

from bettercopilot.ui.gui.api import GUIAPI
from bettercopilot.ui.gui import ai_panel


class MockProvider:
    def __init__(self, name, reply_prefix='R'):
        self.name = name
        self.reply_prefix = reply_prefix
        self.called = 0

    def generate(self, messages, progress_callback=None):
        self.called += 1
        chat = f"{self.reply_prefix} reply {self.called}"
        diff = f"--- a\n+++ b\n@@\n+{self.reply_prefix} change {self.called}\n"
        try:
            if callable(progress_callback):
                progress_callback('provider_stream', {'provider': self.name, 'partial': chat})
        except Exception:
            pass
        return {'text': json.dumps({'chat': chat, 'diffs': [diff]}), 'raw': {'provider': self.name}}


class SimpleEditor:
    def __init__(self, text='initial'):
        self._text = text

    def get_text(self):
        return self._text

    def apply_diff(self, diff_text=None, final_text=None):
        if final_text is not None:
            self._text = final_text
        elif diff_text is not None:
            self._text += '\n' + str(diff_text)

    def set_text(self, t):
        self._text = t

    def save_file(self, *args, **kwargs):
        return True


class DiffViewer:
    def __init__(self):
        self._diff = None

    def set_diff(self, d):
        self._diff = d

    def get_diff(self):
        return self._diff


def run_consensus(task: str, feedback_iters: int = 2):
    gui = GUIAPI()
    panel1 = ai_panel.AIPanel()
    panel2 = ai_panel.AIPanel()
    panel1.set_provider_label('p1')
    panel2.set_provider_label('p2')
    gui.ai_panel = panel1
    gui.ai_panel_ollama = panel2
    gui.diff_viewer = DiffViewer()
    gui.editor = SimpleEditor('start')

    class FakeOrch:
        def __init__(self):
            self.providers = {'p1': MockProvider('p1', 'A'), 'p2': MockProvider('p2', 'B')}

    gui.orchestrator = FakeOrch()

    # Kick off feedback loop via run_ask with /feedback
    w = gui.run_ask(f"/feedback={feedback_iters} {task}", provider_override='p1')

    # Wait for worker to finish if possible
    try:
        if hasattr(w, 'join'):
            w.join(timeout=30)
    except Exception:
        pass

    # Output results for harness parsing
    print('Editor text after feedback:\n', gui.editor.get_text(), flush=True)
    print('Diff viewer diff:\n', gui.diff_viewer.get_diff(), flush=True)
    print('Panel1 history:', panel1.get_history(), flush=True)
    print('Panel2 history:', panel2.get_history(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', required=True, help='Task description to run consensus on')
    parser.add_argument('--iters', type=int, default=2, help='Feedback iterations to request')
    args = parser.parse_args()
    run_consensus(args.task, args.iters)
