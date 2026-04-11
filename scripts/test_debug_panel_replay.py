#!/usr/bin/env python3
import time
from bettercopilot.logging import global_debug
# write a test event
global_debug.write({'ts': time.time(), 'event': 'smoke_test', 'text': 'hello from replay test'})
# import headless DebugPanel and check replay
from bettercopilot.ui.gui.debug_panel import DebugPanel
panel = DebugPanel()
lines = []
try:
    lines = panel.get_lines()
except Exception:
    try:
        # GUI widget path: try reading internal QTextEdit contents
        import inspect
        print('Panel type:', type(panel))
    except Exception:
        pass
# find if smoke_test present
found = any('smoke_test' in l for l in lines)
print('FOUND' if found else 'MISSING')
if not found:
    print('Recent lines length:', len(lines))
    if len(lines) > 0:
        print(lines[-5:])

