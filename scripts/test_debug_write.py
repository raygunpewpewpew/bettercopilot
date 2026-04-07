#!/usr/bin/env python3
import sys
from pathlib import Path
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))

from bettercopilot.ui.gui.api import GUIAPI
from bettercopilot.ui.gui.main_window import HeadlessMainWindow
try:
    # If PySide6 is available, ensure QApplication exists so imports succeed
    from PySide6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication([])
except Exception:
    _app = None

api = GUIAPI()
win = HeadlessMainWindow()
api.bind_frontend(win)
print('api.ai_panel is', type(api.ai_panel), 'has append_debug=', hasattr(api.ai_panel, 'append_debug'), 'has append_message=', hasattr(api.ai_panel, 'append_message'))

# Directly exercise append_debug to verify headless writer
try:
    win.ai_panel.append_debug('direct-test-entry')
    print('direct append_debug called')
    try:
        print('immediate _debug list:', getattr(win.ai_panel, '_debug', None))
    except Exception:
        pass
    try:
        print('dir(ai_panel):', sorted([k for k in dir(win.ai_panel) if not k.startswith('__')]))
    except Exception:
        pass
except Exception as e:
    print('direct append_debug failed:', e)

# Remove any existing debug log to test clean write
log = Path.cwd() / 'debug_log.txt'
try:
    if log.exists():
        log.unlink()
except Exception:
    pass

# Emit a few progress events that should trigger append_debug
print('emit events')
api._handle_progress('provider_call_end', {'preview': 'Test preview text', 'data': {'attempt': 1}})
print('after provider_call_end')
api._handle_progress('responding', {'final_output': 'Final response text'})
print('after responding')
api._handle_progress('done', {'task_id': 'test-task-1'})
print('after done')

# Show headless debug entries and on-disk file contents
try:
    if hasattr(win.ai_panel, 'get_debug'):
        dbg = win.ai_panel.get_debug()
    else:
        dbg = []
    print('headless debug entries:', dbg)
except Exception as e:
    print('error reading headless debug:', e)
    # Try calling the GUI panel's private writer directly
    try:
        if hasattr(win.ai_panel, '_write_debug_line'):
            win.ai_panel._write_debug_line('direct-write-entry')
            print('called _write_debug_line')
    except Exception as e:
        print('direct _write_debug_line failed:', e)

# Quick probe to ensure we can write to cwd
try:
    probe = Path.cwd() / 'debug_write_probe.txt'
    with open(probe, 'w', encoding='utf-8') as pf:
        pf.write('probe')
    print('probe file written to', probe)
except Exception as e:
    print('probe write failed:', e)

if log.exists():
    print('\nfile lines:')
    try:
        for line in log.read_text(encoding='utf-8').splitlines():
            print(line)
    except Exception as e:
        print('error reading file:', e)
else:
    print('no debug file found at', log)
