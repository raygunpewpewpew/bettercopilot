"""Application entrypoint for the PySide6 GUI. Falls back to headless facade when PySide6 is absent."""
from typing import Optional

try:
    from PySide6.QtWidgets import QApplication
    PYSIDE = True
except Exception:
    PYSIDE = False

from .main_window import MainWindow
from .api import GUIAPI


def run_gui(argv=None, orchestrator=None, workspace_path: Optional[str] = None):
    api = GUIAPI(orchestrator=orchestrator)
    win = MainWindow()
    # always bind frontend so API can update panels in headless and GUI modes
    try:
        api.bind_frontend(win)
    except Exception:
        pass

    if PYSIDE:
        app = QApplication(argv or [])
        try:
            win.wiring(api)
        except Exception:
            pass
        win.show()
        return app.exec()
    else:
        # headless: return main window facade with API bound
        return win
