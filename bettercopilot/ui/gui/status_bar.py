"""Status bar for the GUI with simple notifications. Headless fallback included."""
from typing import Optional

try:
    from PySide6.QtWidgets import QStatusBar, QLabel
    from PySide6.QtCore import Signal
    PYSIDE = True
except Exception:
    PYSIDE = False


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
    class StatusBar(QStatusBar):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._label = QLabel('Ready')
            self.addWidget(self._label)

        def set_message(self, msg: Optional[str]):
            try:
                # QStatusBar provides showMessage; use it for consistency
                self.showMessage(msg or '')
            except Exception:
                try:
                    self._label.setText(msg or '')
                except Exception:
                    pass

else:
    class StatusBar:
        def __init__(self):
            self._message = 'Ready'

        def set_message(self, msg: Optional[str]):
            self._message = msg or ''

        def get_message(self) -> str:
            return self._message
