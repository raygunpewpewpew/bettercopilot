"""Status bar for the GUI with simple notifications. Headless fallback included."""
from typing import Optional

try:
    from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
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
    class StatusBar(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.layout = QHBoxLayout()
            self.label = QLabel('Ready')
            self.layout.addWidget(self.label)
            self.setLayout(self.layout)

        def set_message(self, msg: Optional[str]):
            self.label.setText(msg or '')

else:
    class StatusBar:
        def __init__(self):
            self._message = 'Ready'

        def set_message(self, msg: Optional[str]):
            self._message = msg or ''

        def get_message(self) -> str:
            return self._message
