#!/usr/bin/env python3
r"""Launch the native GUI, send an automated ask to the AI panel, and quit after response.

Usage:
    python scripts/gui_auto_ask.py

This script is intended for local interactive debugging: it will open the
native PySide6 window, submit a short prompt via the GUI API, print the
result to the terminal, and quit automatically after the response (or
after 20 seconds as a fallback).
"""
import sys
import traceback
from pathlib import Path
import json

root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    PYSIDE = True
except Exception:
    PYSIDE = False

try:
    from bettercopilot.ui.gui.main_window import MainWindow
    from bettercopilot.ui.gui.api import GUIAPI
except Exception as e:
    print('IMPORT_ERROR', e)
    traceback.print_exc()
    sys.exit(2)

message = "Hello from BetterCopilot GUI automated test. Please say a short greeting."
if len(sys.argv) > 1:
    message = sys.argv[1]

if not PYSIDE:
    print('PySide6 not available; cannot open native GUI')
    sys.exit(3)

app = QApplication(sys.argv)
win = MainWindow()
api = GUIAPI()
api.bind_frontend(win)
try:
    win.wiring(api)
except Exception as e:
    print('WIRING_ERROR', e)

win.show()

from PySide6.QtCore import QTimer

def on_result(res):
    try:
        print('\n--- ASK_RESULT ---')
        if isinstance(res, dict):
            # Best-effort print of final_text or whole result
            out = res.get('final_text') or res.get('text') or res
            print(out)
            # Also write result to a file for verification
            try:
                out_path = Path(__file__).parent / 'gui_auto_ask_result.json'
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump({'result': out}, f, ensure_ascii=False, indent=2)
            except Exception as _e:
                print('WRITE_RESULT_FAILED', _e)
        else:
            print(res)
    except Exception:
        traceback.print_exc()
    # Quit shortly after receiving result so UI updates are visible briefly
    QTimer.singleShot(200, app.quit)


def on_error(err):
    print('\n--- ASK_ERROR ---')
    print(str(err))
    traceback.print_exc()
    QTimer.singleShot(200, app.quit)

# Submit the ask via GUI API; GUIAPI will update the ai_panel when finished.
worker = None
try:
    worker = api.run_ask(message, callback=on_result, error_callback=on_error)
    print('run_ask started, worker:', type(worker))
except Exception as e:
    print('RUN_ASK_FAILED', e)
    traceback.print_exc()
    QTimer.singleShot(200, app.quit)

# Also attach worker-level callbacks as a fallback in case the API-level
# callback wrapper swallows the user callback for any reason.
try:
    if worker is not None:
        try:
            if hasattr(worker, 'finished'):
                worker.finished.connect(on_result)
        except Exception as _e:
            print('FAILED to connect finished callback to worker:', _e)
        try:
            if hasattr(worker, 'error'):
                worker.error.connect(on_error)
        except Exception as _e:
            print('FAILED to connect error callback to worker:', _e)
except Exception:
    pass

# Fallback: quit after 20s in case the request hangs
QTimer.singleShot(20000, app.quit)
app.exec()
print('gui_auto_ask finished')
