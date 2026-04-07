#!/usr/bin/env python3
r"""Demo: open the native GUI and programmatically ask a question.

The GUI stays open so you can watch the AI panel update. Close the window
when you're done to end the demo.
"""
import sys, traceback, os
from pathlib import Path

root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    PYSIDE = True
except Exception:
    PYSIDE = False

if not PYSIDE:
    print('PySide6 not available; run the GUI interactively with run_gui.bat')
    sys.exit(1)

try:
    from bettercopilot.ui.gui.main_window import MainWindow
    from bettercopilot.ui.gui.api import GUIAPI
except Exception as e:
    print('IMPORT_ERROR', e)
    traceback.print_exc()
    sys.exit(2)

app = QApplication(sys.argv)
win = MainWindow()
# Load OpenRouter key from system keyring if available so providers initialize
try:
    import keyring
except Exception:
    keyring = None

if keyring and not os.environ.get('OPENROUTER_API_KEY'):
    try:
        _k = keyring.get_password('bettercopilot', 'openrouter')
        if _k:
            os.environ['OPENROUTER_API_KEY'] = _k
            print('Loaded OPENROUTER_API_KEY from keyring')
    except Exception:
        pass

api = GUIAPI()
# Enable fast direct-provider chat for the demo so responses appear quickly
try:
    api.set_direct_chat(True)
    print('Direct provider chat enabled for demo')
except Exception:
    pass
api.bind_frontend(win)
try:
    win.wiring(api)
except Exception as e:
    print('WIRING_ERROR', e)

win.show()

message = "Hello from GUI demo — please say a short greeting."
print('Scheduling demo ask:', message)

def do_ask():
    print('Sending demo ask...')
    def on_result(res):
        try:
            print('\n--- DEMO RESULT ---')
            text = None
            if isinstance(res, dict):
                text = res.get('final_text')
                if not text:
                    # Search logs for provider preview
                    logs = res.get('logs') or []
                    for entry in reversed(logs):
                        if isinstance(entry, dict) and 'output_preview' in entry:
                            text = entry.get('output_preview')
                            break
                if not text:
                    # Try raw fields
                    text = str(res.get('raw') or res)
            else:
                text = str(res)
            print(text)
            try:
                if api.ai_panel:
                    api.ai_panel.append_message('assistant', text)
            except Exception:
                pass
        except Exception:
            traceback.print_exc()

    def on_error(err):
        print('\n--- DEMO ERROR ---')
        print(err)

    try:
        # Populate the AI panel UI so the question is visible to the user
        try:
            if api.ai_panel:
                try:
                    if hasattr(api.ai_panel, 'input'):
                        api.ai_panel.input.setText(message)
                    if hasattr(api.ai_panel, 'append_message'):
                        api.ai_panel.append_message('user', message)
                except Exception:
                    pass
        except Exception:
            pass

        api.run_ask(message, callback=on_result, error_callback=on_error)
    except Exception as e:
        print('RUN_ASK_FAILED', e)
        traceback.print_exc()

# Schedule shortly after event loop starts so window appears first
QTimer.singleShot(300, do_ask)

print('GUI opened. The window will remain open; close it to finish the demo.')
app.exec()
print('Demo finished')
