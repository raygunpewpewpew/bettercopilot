#!/usr/bin/env python3
"""Check importing PySide6.QtWidgets and print full traceback on failure.

Run with the exact interpreter you plan to use for the GUI, for example:
  & 'C:\full\path\to\python.exe' scripts/check_qtwidgets.py
"""
import traceback
import sys

print('Using python:', sys.executable)
try:
    import PySide6
    print('PySide6 version:', getattr(PySide6, '__version__', None))
except Exception:
    print('Failed to import PySide6:')
    traceback.print_exc()
    sys.exit(2)

try:
    from PySide6 import QtWidgets
    print('Imported PySide6.QtWidgets: OK')
    try:
        print('QApplication:', QtWidgets.QApplication)
    except Exception:
        pass
except Exception:
    print('Failed to import PySide6.QtWidgets:')
    traceback.print_exc()
    sys.exit(3)

print('All PySide6.QtWidgets imports succeeded')
