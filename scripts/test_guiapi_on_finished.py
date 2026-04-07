#!/usr/bin/env python3
"""Headless test: verify GUIAPI._on_task_finished appends assistant message to headless ai_panel."""
import sys
from pathlib import Path
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))

from bettercopilot.ui.gui.api import GUIAPI
from bettercopilot.ui.gui.main_window import HeadlessMainWindow
try:
    # If PySide6 is available, create a QApplication so QWidget construction succeeds
    from PySide6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication([])
except Exception:
    _app = None

api = GUIAPI()
win = HeadlessMainWindow()
api.bind_frontend(win)

# Simulate an orchestrator result without final_text but with logs output_preview
res = {
    'task_id': 'test-1',
    'final_text': None,
    'logs': [
        {'attempt': 1, 'provider': 'openrouter', 'elapsed': 0.5, 'output_preview': "Hello from provider preview."}
    ],
    'critic_feedback': [],
    'diffs': []
}

api._on_task_finished(res)

if hasattr(win.ai_panel, 'get_history'):
    history = win.ai_panel.get_history()
    print('History:', history)
    if history and history[-1].get('text'):
        print('PASS: assistant message appended')
        sys.exit(0)
    else:
        print('FAIL: no assistant message in headless history')
        sys.exit(2)
else:
    # Try to read from QTextEdit (PySide UI)
    try:
        txt = ''
        if hasattr(win.ai_panel, 'history') and hasattr(win.ai_panel.history, 'toPlainText'):
            txt = win.ai_panel.history.toPlainText()
        print('QTextEdit content:', repr(txt))
        if txt and 'Hello from provider preview.' in txt:
            print('PASS: assistant message appended to QTextEdit')
            sys.exit(0)
        else:
            print('FAIL: no assistant message in QTextEdit')
            sys.exit(2)
    except Exception as e:
        print('ERROR reading QTextEdit:', e)
        sys.exit(3)
