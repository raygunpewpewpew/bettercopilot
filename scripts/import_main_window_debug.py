#!/usr/bin/env python3
import traceback, sys, importlib
from pathlib import Path

# Ensure project root is on sys.path so package imports resolve the
# workspace 'bettercopilot' package instead of treating the scripts
# directory as the top-level package root.
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))
print('python:', sys.executable)
print('sys.path[0]=', sys.path[0])
try:
    m = importlib.import_module('bettercopilot.ui.gui.main_window')
    print('Imported main_window; PYSIDE=', getattr(m,'PYSIDE', None))
    print('MainWindow:', getattr(m, 'MainWindow', None))
except Exception:
    traceback.print_exc()
