# debug runner for GUI: prints status, shows window for 2s, then exits
import sys
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    PYSIDE = True
except Exception as e:
    print('PySide6 import failed:', e)
    PYSIDE = False

print('PYSIDE:', PYSIDE)

if PYSIDE:
    try:
        from bettercopilot.ui.gui.main_window import MainWindow
        print('Imported MainWindow')
        app = QApplication(sys.argv)
        win = MainWindow()
        print('Created MainWindow')
        win.show()
        print('Window shown; will quit in 2 seconds...')
        QTimer.singleShot(2000, app.quit)
        app.exec()
        print('Event loop finished')
    except Exception as e:
        print('Exception while creating or running GUI:', e)
else:
    print('Running headless MainWindow')
    from bettercopilot.ui.gui.main_window import MainWindow
    win = MainWindow()
    print('Headless MainWindow created')
    # exercise binding briefly
    from bettercopilot.ui.gui.api import GUIAPI
    api = GUIAPI()
    api.bind_frontend(win)
    print('API bound to headless window')
print('Done')
