"""Global Debug Panel widget and headless fallback.

The panel registers a callback with `bettercopilot.logging.global_debug` to
receive events in real time and display them in a single consolidated view.
"""
from typing import Optional

try:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
    from PySide6.QtCore import Qt
    PYSIDE = True
except Exception:
    PYSIDE = False

try:
    from bettercopilot.logging import global_debug
except Exception:
    global_debug = None


if PYSIDE:
    class DebugPanel(QWidget):
        def __new__(cls, *args, **kwargs):
            try:
                from PySide6.QtCore import QCoreApplication
                if QCoreApplication.instance() is None:
                    class _Headless:
                        def __init__(self, parent=None):
                            self._lines = []
                            try:
                                if global_debug is not None:
                                    global_debug.register_callback(self._on_event)
                            except Exception:
                                pass

                        def _on_event(self, event: dict):
                            try:
                                import json
                                s = json.dumps(event, ensure_ascii=False)
                                self._lines.append(s)
                            except Exception:
                                try:
                                    self._lines.append(str(event))
                                except Exception:
                                    pass

                        def append_line(self, s: str):
                            try:
                                self._lines.append(str(s))
                            except Exception:
                                pass

                        def get_lines(self):
                            return list(self._lines)

                    return _Headless(*args, **kwargs)
            except Exception:
                pass
            return super().__new__(cls)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.layout = QVBoxLayout()
            try:
                label = QLabel('Debug')
                label.setStyleSheet('font-weight: bold;')
                self.layout.addWidget(label)
            except Exception:
                pass
            self.debug_view = QTextEdit()
            self.debug_view.setReadOnly(True)
            self.debug_view.setMinimumHeight(120)
            self.layout.addWidget(self.debug_view)

            # Toggle button placed under the field per user request.
            self.toggle_btn = QPushButton('Hide Debug')
            self.toggle_btn.setCheckable(True)
            self.toggle_btn.setChecked(False)
            self.toggle_btn.clicked.connect(self._on_toggle)
            self.layout.addWidget(self.toggle_btn)

            self.setLayout(self.layout)

            # Register callback to receive global debug events
            try:
                if global_debug is not None:
                    global_debug.register_callback(self._on_event)
            except Exception:
                pass

        def _on_toggle(self, checked):
            try:
                if checked:
                    self.debug_view.hide()
                    self.toggle_btn.setText('Show Debug')
                else:
                    self.debug_view.show()
                    self.toggle_btn.setText('Hide Debug')
            except Exception:
                pass

        def _on_event(self, event: dict):
            try:
                import json
                s = json.dumps(event, ensure_ascii=False, indent=2)
                try:
                    self.debug_view.append(s)
                    self.debug_view.append('')
                except Exception:
                    pass
            except Exception:
                pass

        def append_line(self, s: str):
            try:
                self.debug_view.append(s)
            except Exception:
                pass
else:
    class DebugPanel:
        def __init__(self):
            self._lines = []
            try:
                if global_debug is not None:
                    global_debug.register_callback(self._on_event)
            except Exception:
                pass

        def _on_event(self, event: dict):
            try:
                import json
                s = json.dumps(event, ensure_ascii=False)
                self._lines.append(s)
            except Exception:
                try:
                    self._lines.append(str(event))
                except Exception:
                    pass

        def append_line(self, s: str):
            try:
                self._lines.append(str(s))
            except Exception:
                pass

        def get_lines(self):
            return list(self._lines)
