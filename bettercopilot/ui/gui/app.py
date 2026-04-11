"""Application entrypoint for the PySide6 GUI. Falls back to headless facade when PySide6 is absent."""
from typing import Optional
import time
from pathlib import Path

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

try:
    # Log PYSIDE detection at module import time for diagnostics
    try:
        from bettercopilot.logging import global_debug
        try:
            global_debug.write({'ts': time.time(), 'event': 'app_module_imported', 'PYSIDE': PYSIDE})
        except Exception:
            pass
    except Exception:
        pass
except Exception:
    pass


def run_gui(argv=None, orchestrator=None, workspace_path: Optional[str] = None):
    try:
        # record entry to run_gui early for startup tracing
        try:
            from bettercopilot.logging import global_debug
            try:
                global_debug.write({'ts': time.time(), 'event': 'run_gui_entered', 'PYSIDE': PYSIDE})
            except Exception:
                pass
        except Exception:
            pass
    except Exception:
        pass
    try:
        api = GUIAPI(orchestrator=orchestrator)
        try:
            from bettercopilot.logging import global_debug
            try:
                global_debug.write({'ts': time.time(), 'event': 'guiapi_initialized'})
            except Exception:
                pass
        except Exception:
            pass
        # direct fallback write for startup tracing (avoid global_debug dependency)
        try:
            try:
                p = Path.cwd() / 'DebugLogs' / 'direct_startup.log'
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(f"{time.time()} guiapi_initialized PYSIDE={PYSIDE}\n")
            except Exception:
                pass
        except Exception:
            pass
    except Exception as e:
        try:
            from bettercopilot.logging import global_debug
            try:
                global_debug.write({'ts': time.time(), 'event': 'guiapi_init_failed', 'error': str(e)})
            except Exception:
                pass
        except Exception:
            pass
        raise
    # Initialize centralized debug logging and lightweight tracing for GUI runs.
    try:
        # direct trace marker before attempting to start_tracing
        try:
            p = Path.cwd() / 'DebugLogs' / 'direct_startup.log'
            try:
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(f"{time.time()} before_start_tracing\n")
            except Exception:
                pass
        except Exception:
            pass
        from bettercopilot.logging import global_debug
        try:
            # Avoid enabling heavy tracing at startup; install only exception hook.
            try:
                p = Path.cwd() / 'DebugLogs' / 'direct_startup.log'
                try:
                    with open(p, 'a', encoding='utf-8') as f:
                        f.write(f"{time.time()} skipping_start_tracing\n")
                except Exception:
                    pass
            except Exception:
                pass
            try:
                global_debug.install_exception_hook()
            except Exception:
                pass
        except Exception:
            pass
    except Exception:
        pass
    # Print startup info so it's clear which Python interpreter is running
    # and whether PySide6 is available for the native GUI.
    try:
        import sys
        print(f"Starting BetterCopilot GUI using Python executable: {sys.executable}")
        try:
            from bettercopilot.logging import global_debug
            try:
                global_debug.write({'ts': time.time(), 'event': 'run_gui_start', 'PYSIDE': PYSIDE, 'python': sys.executable})
            except Exception:
                pass
        except Exception:
            pass
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
        try:
            try:
                from bettercopilot.logging import global_debug
                try:
                    global_debug.write({'ts': time.time(), 'event': 'creating_qapplication'})
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass
        try:
            p = Path.cwd() / 'DebugLogs' / 'direct_startup.log'
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(f"{time.time()} creating_qapplication\n")
            except Exception:
                pass
        except Exception:
            pass
        app = QApplication(argv or [])
        try:
            from bettercopilot.logging import global_debug
            try:
                global_debug.write({'ts': time.time(), 'event': 'qapplication_created'})
            except Exception:
                pass
        except Exception:
            pass
        try:
            p = Path.cwd() / 'DebugLogs' / 'direct_startup.log'
            try:
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(f"{time.time()} qapplication_created\n")
            except Exception:
                pass
        except Exception:
            pass
        win = MainWindow()
        try:
            from bettercopilot.logging import global_debug
            try:
                global_debug.write({'ts': time.time(), 'event': 'main_window_instantiated', 'class': type(win).__name__})
            except Exception:
                pass
        except Exception:
            pass
        try:
            p = Path.cwd() / 'DebugLogs' / 'direct_startup.log'
            try:
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(f"{time.time()} main_window_instantiated class={type(win).__name__}\n")
            except Exception:
                pass
        except Exception:
            pass
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
        try:
            try:
                if hasattr(win, 'raise_'):
                    try:
                        win.raise_()
                    except Exception:
                        pass
                if hasattr(win, 'activateWindow'):
                    try:
                        win.activateWindow()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass
        try:
            p = Path.cwd() / 'DebugLogs' / 'direct_startup.log'
            try:
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(f"{time.time()} main_window_show_called\n")
            except Exception:
                pass
        except Exception:
            pass
        try:
            try:
                from bettercopilot.logging import global_debug
                try:
                    global_debug.write({'ts': time.time(), 'event': 'main_window_shown'})
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass
        return app.exec()
    else:
        # headless: construct main window facade and bind API
        win = MainWindow()
        try:
            p = Path.cwd() / 'DebugLogs' / 'direct_startup.log'
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(f"{time.time()} headless_main_window_instantiated class={type(win).__name__}\n")
            except Exception:
                pass
        except Exception:
            pass
        try:
            api.bind_frontend(win)
        except Exception:
            pass
        return win


if __name__ == "__main__":
    # When executed as a script, start the GUI. This allows
    # `python bettercopilot/ui/gui/app.py` (from project root) to work.
    run_gui()
