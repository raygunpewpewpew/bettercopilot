#!/usr/bin/env python3
"""Local debug runner for the GUI.

Run this from the project root to get console feedback before the Qt
event loop blocks. It shows whether PySide6 is available, imports the
MainWindow, displays it for 3s, then exits.
"""
import sys
from pathlib import Path

root = Path(__file__).parent.resolve()
print('Project root:', root)
sys.path.insert(0, str(root))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    PYSIDE = True
    print('PySide6 import: OK')
except Exception as e:
    PYSIDE = False
    print('PySide6 import failed:', e)

if PYSIDE:
    try:
        from bettercopilot.ui.gui.main_window import MainWindow
        print('Imported MainWindow')
        app = QApplication(sys.argv)
        win = MainWindow()
        print('Created MainWindow')
        win.show()
        # try to bring window to front and print geometry for debugging
        try:
            win.raise_()
            win.activateWindow()
        except Exception:
            pass

        try:
            geom = win.geometry()
            print('Window geometry: x=%s y=%s w=%s h=%s' % (geom.x(), geom.y(), geom.width(), geom.height()))
            screen = app.primaryScreen()
            if screen:
                sgeom = screen.availableGeometry()
                print('Screen available geometry: x=%s y=%s w=%s h=%s' % (sgeom.x(), sgeom.y(), sgeom.width(), sgeom.height()))
                # center window on the primary screen for visibility
                try:
                    cx = sgeom.x() + (sgeom.width() - geom.width()) // 2
                    cy = sgeom.y() + (sgeom.height() - geom.height()) // 2
                    win.move(cx, cy)
                    print('Moved window to center: x=%s y=%s' % (cx, cy))
                except Exception as e:
                    print('Failed to move window:', e)
        except Exception as e:
            print('Failed to query geometry:', e)

        print('Window shown; will quit automatically in 5 seconds...')
        QTimer.singleShot(5000, app.quit)
        app.exec()
        print('Event loop finished')
    except Exception as e:
        print('Exception while running GUI:', e)
else:
    print('PySide6 not available; running headless check')
    try:
        from bettercopilot.ui.gui.main_window import MainWindow
        from bettercopilot.ui.gui.api import GUIAPI
        win = MainWindow()
        print('Headless MainWindow created')
        api = GUIAPI()
        api.bind_frontend(win)
        print('API bound to headless window')
    except Exception as e:
        print('Headless check failed:', e)

print('Debug runner done')
