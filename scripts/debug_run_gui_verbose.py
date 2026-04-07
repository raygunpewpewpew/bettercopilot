#!/usr/bin/env python3
r"""Verbose GUI debugger: prints module-level PYSIDE and MainWindow type before showing window.

Run with the interpreter you want to test, for example:
    & 'C:\Users\surfing\AppData\Local\Programs\Python\Python313\python.exe' scripts/debug_run_gui_verbose.py
"""
import sys, traceback
from pathlib import Path

root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))

print('Project root:', root)

try:
    import PySide6
    print('PySide6 import OK:', getattr(PySide6, '__version__', None))
except Exception as e:
    print('PySide6 import failed in verbose runner:', e)

try:
    import importlib
    m = importlib.import_module('bettercopilot.ui.gui.main_window')
    print('Imported module:', m.__name__)
    print('module.PYSIDE =', getattr(m, 'PYSIDE', None))
    MainWindow = getattr(m, 'MainWindow', None)
    print('MainWindow:', MainWindow)
    try:
        print('MainWindow.__name__ =', MainWindow.__name__)
    except Exception:
        pass

    # If PySide is available, attempt to create a QApplication and show the window
    if getattr(m, 'PYSIDE', False):
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QTimer
            app = QApplication(sys.argv)
            win = MainWindow()
            print('Created window instance:', type(win))
            try:
                # check if this window has geometry
                geom = win.geometry()
                print('Window geometry ok: ', geom.x(), geom.y(), geom.width(), geom.height())
            except Exception as e:
                print('Window geometry query failed:', e)
            try:
                win.show()
                print('Window shown; will quit automatically in 5s')
                QTimer.singleShot(5000, app.quit)
                app.exec()
                print('Event loop finished')
            except Exception:
                print('Exception while showing window:')
                traceback.print_exc()
        except Exception:
            print('Failed to run PySide GUI:')
            traceback.print_exc()
    else:
        print('Module thinks PySide is not available; showing headless info')
        try:
            win = MainWindow()
            print('Headless window type:', type(win))
        except Exception:
            print('Failed to instantiate headless window:')
            traceback.print_exc()

except Exception:
    print('Failed to import main_window module:')
    traceback.print_exc()

print('Verbose debug runner done')
