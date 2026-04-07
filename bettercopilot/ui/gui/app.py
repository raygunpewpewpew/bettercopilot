"""Application entrypoint for the PySide6 GUI. Falls back to headless facade when PySide6 is absent."""
from typing import Optional

try:
    from PySide6.QtWidgets import QApplication
    PYSIDE = True
except Exception:
    PYSIDE = False

try:
    from .main_window import MainWindow
    from .api import GUIAPI
except Exception:
    # Allow running this file directly as a script (no package context).
    # Fall back to absolute imports when relative imports fail.
    from bettercopilot.ui.gui.main_window import MainWindow
    from bettercopilot.ui.gui.api import GUIAPI


def run_gui(argv=None, orchestrator=None, workspace_path: Optional[str] = None):
    api = GUIAPI(orchestrator=orchestrator)
    # Print startup info so it's clear which Python interpreter is running
    # and whether PySide6 is available for the native GUI.
    try:
        import sys
        print(f"Starting BetterCopilot GUI using Python executable: {sys.executable}")
        if PYSIDE:
            try:
                import PySide6
                pv = getattr(PySide6, '__version__', 'unknown')
                ppath = getattr(PySide6, '__file__', 'unknown')
                print(f"PySide6 available: version={pv} path={ppath}")
            except Exception as e:
                print('PySide6 runtime import failed:', e)
        else:
            print('PySide6 not available; GUI will run headless (no native window).')
    except Exception:
        # Do not let debug logging break runtime.
        pass
    # In GUI mode, construct QApplication before creating any QWidget instances.
    if PYSIDE:
        app = QApplication(argv or [])
        win = MainWindow()
        # bind frontend so API can update panels
        try:
            api.bind_frontend(win)
        except Exception:
            pass
        try:
            win.wiring(api)
        except Exception:
            pass
        win.show()
        return app.exec()
    else:
        # headless: construct main window facade and bind API
        win = MainWindow()
        try:
            api.bind_frontend(win)
        except Exception:
            pass
        return win


if __name__ == "__main__":
    # When executed as a script, start the GUI. This allows
    # `python bettercopilot/ui/gui/app.py` (from project root) to work.
    run_gui()
