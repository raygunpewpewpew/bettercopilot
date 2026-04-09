"""Editor panel: text editing widget with headless fallback.

Provides: load_file, get_text, set_text, apply_diff (accept final_text optional), save_file
"""
import os
from typing import Optional
import re

try:
    from PySide6.QtWidgets import QWidget, QPlainTextEdit, QVBoxLayout, QLabel
    from PySide6.QtGui import QFont
    PYSIDE = True
except Exception:
    PYSIDE = False


class EditorPanelBase:
    def load_file(self, path: str):
        raise NotImplementedError

    def get_text(self) -> str:
        raise NotImplementedError

    def set_text(self, text: str):
        raise NotImplementedError

    def save_file(self, path: Optional[str] = None):
        raise NotImplementedError

    def apply_diff(self, diff_text: str = None, final_text: str = None):
        # If final_text provided, apply it; otherwise do nothing (headless fallback)
        raise NotImplementedError


if PYSIDE:
    class EditorPanel(QWidget, EditorPanelBase):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.editor = QPlainTextEdit()
            self.editor.setFont(QFont('Courier', 10))
            try:
                # Ensure a white editing background for clarity per user request
                self.editor.setStyleSheet('background: white; color: black;')
            except Exception:
                pass
            layout = QVBoxLayout()
            try:
                label = QLabel('Editor')
                try:
                    label.setStyleSheet('font-weight: bold;')
                except Exception:
                    pass
                layout.addWidget(label)
            except Exception:
                pass
            layout.addWidget(self.editor)
            self.setLayout(layout)
            self._current_path = None

        def load_file(self, path: str):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            self.editor.setPlainText(text)
            self._current_path = path

        def get_text(self) -> str:
            return self.editor.toPlainText()

        def set_text(self, text: str):
            self.editor.setPlainText(text)

        def save_file(self, path: Optional[str] = None):
            p = path or self._current_path
            if not p:
                return False
            with open(p, 'w', encoding='utf-8') as f:
                f.write(self.get_text())
            return True

        def apply_diff(self, diff_text: str = None, final_text: str = None):
            # Prefer explicit final_text. If absent, try to apply unified diff.
            if final_text is not None:
                self.set_text(final_text)
                return
            if diff_text:
                try:
                    orig = self.get_text()
                    patched = _apply_unified_diff(orig, diff_text)
                    self.set_text(patched)
                except Exception:
                    # fallback: do nothing
                    pass

else:
    class EditorPanel(EditorPanelBase):
        def __init__(self):
            self._text = ''
            self._path = None

        def load_file(self, path: str):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                self._text = f.read()
            self._path = path

        def get_text(self) -> str:
            return self._text

        def set_text(self, text: str):
            self._text = text

        def save_file(self, path: Optional[str] = None):
            p = path or self._path
            if not p:
                return False
            with open(p, 'w', encoding='utf-8') as f:
                f.write(self._text)
            return True

        def apply_diff(self, diff_text: str = None, final_text: str = None):
            if final_text is not None:
                return
            if diff_text:
                try:
                    self._text = _apply_unified_diff(self._text, diff_text)
                except Exception:
                    pass
                self._text = final_text
def _apply_unified_diff(original_text: str, diff_text: str) -> str:
    """Apply a unified diff (as produced by difflib.unified_diff) to original_text.

    This is a lightweight best-effort applier: it parses hunks and applies
    additions/removals. It returns the patched text. Line endings are normalized
    to '\n' and a trailing newline is preserved if present in the original.
    """
    if not diff_text:
        return original_text

    orig_lines = original_text.splitlines()
    diff_lines = diff_text.splitlines()
    patched: list[str] = []
    orig_idx = 0
    i = 0
    header_re = re.compile(r'^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@')

    while i < len(diff_lines):
        line = diff_lines[i]
        m = header_re.match(line)
        if m:
            old_start = int(m.group('old_start'))
            # old_count = int(m.group('old_count') or '1')
            old_index = old_start - 1
            # copy unchanged block before hunk
            if old_index > orig_idx:
                patched.extend(orig_lines[orig_idx:old_index])
            orig_idx = old_index
            i += 1
            # process hunk lines
            while i < len(diff_lines) and not diff_lines[i].startswith('@@'):
                dl = diff_lines[i]
                if not dl:
                    i += 1
                    continue
                prefix = dl[0]
                content = dl[1:]
                if prefix == ' ':
                    # context: copy from original if available
                    if orig_idx < len(orig_lines):
                        patched.append(orig_lines[orig_idx])
                        orig_idx += 1
                    else:
                        patched.append(content)
                elif prefix == '-':
                    # removal: skip original line
                    orig_idx += 1
                elif prefix == '+':
                    # addition: add new line
                    patched.append(content)
                elif dl.startswith('\\ No newline'):
                    # ignore
                    pass
                else:
                    # unknown line type: ignore
                    pass
                i += 1
        else:
            i += 1

    # append remaining original lines
    if orig_idx < len(orig_lines):
        patched.extend(orig_lines[orig_idx:])

    # preserve trailing newline if original had one
    result = '\n'.join(patched)
    if original_text.endswith('\n'):
        result = result + '\n' if not result.endswith('\n') else result
    return result
