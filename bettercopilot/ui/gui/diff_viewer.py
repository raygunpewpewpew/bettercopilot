"""Diff viewer panel for showing and applying diffs. Headless fallback included."""
from typing import List, Dict

try:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
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
    class DiffViewer(QWidget):
        apply_patch = Signal(dict)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.layout = QVBoxLayout()
            self.text = QTextEdit()
            self.text.setReadOnly(True)
            self.btn_row = QHBoxLayout()
            self.btn_apply = QPushButton('Apply Patch')
            self.btn_copy = QPushButton('Copy')
            self.btn_row.addWidget(self.btn_apply)
            self.btn_row.addWidget(self.btn_copy)
            self.layout.addWidget(self.text)
            self.layout.addLayout(self.btn_row)
            self.setLayout(self.layout)
            self.btn_apply.clicked.connect(self._on_apply)

        def _on_apply(self):
            content = self.text.toPlainText()
            # naive: emit full text as patch
            self.apply_patch.emit({'patch': content})

        def set_diff(self, diff_text: str):
            self.text.setPlainText(diff_text)

else:
    class DiffViewer:
        def __init__(self):
            self.apply_patch = SimpleSignal()
            self._diff_text = ''

        def set_diff(self, diff_text: str):
            self._diff_text = diff_text

        def get_diff(self) -> str:
            return self._diff_text
