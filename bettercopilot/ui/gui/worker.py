"""Worker abstraction for running long tasks without blocking the GUI.

Provides a PySide6-aware worker when available and a simple threading-based
fallback for headless operation and tests.
"""
from typing import Callable, Any
import threading

try:
    from PySide6.QtCore import QObject, Signal
    PYSIDE = True
except Exception:
    PYSIDE = False

# If PySide6 is importable but no QApplication instance exists (headless tests),
# prefer the simple threading fallback to avoid using Qt QObject/Signal machinery
# which can cause crashes when the Qt event loop is not running.
#
if PYSIDE:
    try:
        from PySide6.QtCore import QCoreApplication
        if QCoreApplication.instance() is None:
            PYSIDE = False
    except Exception:
        pass

class SimpleSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, cb):
        self._callbacks.append(cb)

    def emit(self, *args, **kwargs):
        for cb in list(self._callbacks):
            try:
                cb(*args, **kwargs)
            except Exception:
                pass


if PYSIDE:
    class Worker(QObject):
        started = Signal()
        progress = Signal(object)
        finished = Signal(object)
        error = Signal(object)

        def __init__(self, fn: Callable, *args, **kwargs):
            super().__init__()
            self._fn = fn
            self._args = args
            self._kwargs = kwargs

        def start(self):
            def _run():
                try:
                    self.started.emit()
                    res = self._fn(*self._args, **self._kwargs)
                    self.finished.emit(res)
                except Exception as e:
                    # Best-effort: log worker exception to global debug before emitting
                    try:
                        import traceback, time
                        try:
                            from bettercopilot.logging import global_debug
                            global_debug.write({'ts': time.time(), 'event': 'worker_exception', 'error': str(e), 'trace': traceback.format_exc()})
                        except Exception:
                            pass
                    except Exception:
                        pass
                    self.error.emit(e)

            t = threading.Thread(target=_run, daemon=True)
            t.start()

else:
    class Worker:
        def __init__(self, fn: Callable, *args, **kwargs):
            self._fn = fn
            self._args = args
            self._kwargs = kwargs
            self.started = SimpleSignal()
            self.progress = SimpleSignal()
            self.finished = SimpleSignal()
            self.error = SimpleSignal()
            self._thread = None

        def start(self):
            def _run():
                try:
                    self.started.emit()
                    res = self._fn(*self._args, **self._kwargs)
                    self.finished.emit(res)
                except Exception as e:
                    # Best-effort: log worker exception to global debug before emitting
                    try:
                        import traceback, time
                        try:
                            from bettercopilot.logging import global_debug
                            global_debug.write({'ts': time.time(), 'event': 'worker_exception', 'error': str(e), 'trace': traceback.format_exc()})
                        except Exception:
                            pass
                    except Exception:
                        pass
                    self.error.emit(e)

            self._thread = threading.Thread(target=_run, daemon=True)
            self._thread.start()

        def join(self, timeout: float = None):
            if self._thread:
                self._thread.join(timeout)
