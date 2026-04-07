"""AI panel: conversation, input, and controls. Headless fallback included."""
from typing import List, Dict, Optional

try:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout
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
    class AIPanel(QWidget):
        ask = Signal(str)
        fix_current_file = Signal()
        run_task = Signal(dict)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.layout = QVBoxLayout()
            self.history = QTextEdit()
            self.history.setReadOnly(True)
            self.input = QLineEdit()
            self.btn_row = QHBoxLayout()
            self.btn_ask = QPushButton('Ask')
            self.btn_fix = QPushButton('Fix File')
            self.btn_run = QPushButton('Run Task')
            self.btn_clear = QPushButton('Clear')
            self.btn_row.addWidget(self.btn_ask)
            self.btn_row.addWidget(self.btn_fix)
            self.btn_row.addWidget(self.btn_run)
            self.btn_row.addWidget(self.btn_clear)
            self.layout.addWidget(self.history)
            self.layout.addWidget(self.input)
            self.layout.addLayout(self.btn_row)
            self.setLayout(self.layout)

            self.btn_ask.clicked.connect(self._on_ask)
            self.btn_fix.clicked.connect(lambda: self.fix_current_file.emit())
            self.btn_run.clicked.connect(lambda: self.run_task.emit({}))
            self.btn_clear.clicked.connect(self.clear)

        def _on_ask(self):
            text = self.input.text()
            if not text:
                return
            self.history.append(f"User: {text}")
            self.ask.emit(text)
            self.input.clear()

        def append_message(self, role: str, text: str):
            self.history.append(f"[{role}] {text}")

        def clear(self):
            self.history.clear()

else:
    class AIPanel:
        def __init__(self):
            self.ask = SimpleSignal()
            self.fix_current_file = SimpleSignal()
            self.run_task = SimpleSignal()
            self._history = []

        def append_message(self, role: str, text: str):
            self._history.append({'role': role, 'text': text})

        def get_history(self) -> List[Dict]:
            return list(self._history)

        def clear(self):
            self._history.clear()
