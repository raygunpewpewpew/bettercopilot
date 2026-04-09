"""AI panel: conversation, input, and controls. Headless fallback included."""
from typing import List, Dict, Optional
from pathlib import Path
import time
import os
import json

try:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QLabel, QComboBox, QToolButton, QSizePolicy, QMainWindow, QSplitter
    from PySide6.QtCore import Signal, QFileSystemWatcher, QTimer, QCoreApplication, QRegularExpression
    from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
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


# Headless (non-Qt) AIPanel implementation usable even when PySide6 is
# importable but no QApplication instance is running (e.g., headless tests).
class HeadlessAIPanel:
    def __init__(self):
        self.ask = SimpleSignal()
        self.run_task = SimpleSignal()
        self.model_selected = SimpleSignal()
        self._history = []
        self._debug = []
        self._status = ''
        self.provider_name = None
        self._models = []
        self._selected_model = None

    def append_message(self, role: str, text: str):
        try:
            self._history.append({'role': role, 'text': text})
        except Exception:
            self._history.append({'role': role, 'text': str(text)})
        # Console diagnostics for troubleshooting
        try:
            print(f"[AIPanel headless] append_message role={role} len={0 if text is None else len(str(text))}")
        except Exception:
            pass
        # Mirror assistant messages to debug log for troubleshooting
        try:
            if role == 'assistant':
                try:
                    import json, time
                    obj = {'ts': time.time(), 'event': 'assistant_append', 'text': text}
                    try:
                        if getattr(self, 'provider_name', None):
                            obj['provider'] = getattr(self, 'provider_name')
                    except Exception:
                        pass
                    s = json.dumps(obj, ensure_ascii=False)
                    # write to debug_log.txt using same candidate locations as append_debug
                    candidates = [Path.cwd()]
                    try:
                        pkg_root = Path(__file__).resolve().parents[4]
                        candidates.append(pkg_root)
                    except Exception:
                        pass
                    candidates.append(Path.home())
                    for base in candidates:
                        try:
                            logfile = Path(base) / 'debug_log.txt'
                            logfile.parent.mkdir(parents=True, exist_ok=True)
                            with open(logfile, 'a', encoding='utf-8') as f:
                                f.write(s + '\n')
                            break
                        except Exception:
                            continue
                except Exception:
                    pass
        except Exception:
            pass

    def update_last_message(self, role: str, text: str):
        try:
            if len(getattr(self, '_history', [])) > 0 and self._history[-1].get('role') == role:
                self._history[-1]['text'] = text
            else:
                self._history.append({'role': role, 'text': text})
        except Exception:
            try:
                self._history.append({'role': role, 'text': str(text)})
            except Exception:
                pass

    def get_history(self) -> List[Dict]:
        return list(self._history)

    def set_provider_label(self, provider_name: Optional[str]):
        try:
            self.provider_name = provider_name
        except Exception:
            pass

    def set_model_list(self, models: List[str], selected: Optional[str] = None):
        try:
            self._models = list(models or [])
            if selected is not None:
                self._selected_model = selected
                try:
                    self.model_selected.emit(selected)
                except Exception:
                    pass
        except Exception:
            pass

    def set_selected_model(self, model: str):
        try:
            self._selected_model = model
            try:
                self.model_selected.emit(model)
            except Exception:
                pass
        except Exception:
            pass

    def clear(self):
        self._history.clear()

    def append_debug(self, text: str):
        try:
            s = str(text)
            pretty = s
            try:
                obj = json.loads(s)
                try:
                    if getattr(self, 'provider_name', None) and not obj.get('provider'):
                        obj['provider'] = getattr(self, 'provider_name')
                except Exception:
                    pass
                pretty = json.dumps(obj, ensure_ascii=False, indent=2)
            except Exception:
                pretty = s
            self._debug.append(pretty)
            try:
                # write to debug_log.txt with rotation
                candidates = [Path.cwd()]
                try:
                    pkg_root = Path(__file__).resolve().parents[4]
                    candidates.append(pkg_root)
                except Exception:
                    pass
                candidates.append(Path.home())

                logfile = None
                for base in candidates:
                    p = Path(base) / 'debug_log.txt'
                    if p.exists():
                        logfile = p
                        break
                if logfile is None:
                    logfile = Path(candidates[0]) / 'debug_log.txt'

                try:
                    b = len(s.encode('utf-8')) + 1
                    max_bytes = 5 * 1024 * 1024
                    if logfile.exists() and logfile.stat().st_size + b > max_bytes:
                        rotated = logfile.with_name(f"{logfile.stem}_{time.strftime('%Y%m%d_%H%M%S')}.txt")
                        try:
                            logfile.replace(rotated)
                        except Exception:
                            try:
                                logfile.rename(rotated)
                            except Exception:
                                pass
                except Exception:
                    pass

                written = False
                try:
                    logfile.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        json.loads(s)
                        write_s = s
                    except Exception:
                        try:
                            wrap = {'ts': time.time(), 'event': 'debug_line', 'text': s}
                            if getattr(self, 'provider_name', None):
                                wrap['provider'] = getattr(self, 'provider_name')
                            write_s = json.dumps(wrap, ensure_ascii=False)
                        except Exception:
                            write_s = s
                    with open(logfile, 'a', encoding='utf-8') as f:
                        f.write(write_s + "\n")
                    written = True
                except Exception:
                    written = False
                return written
            except Exception:
                pass
        except Exception:
            pass
        return False

    def get_debug(self) -> List[str]:
        return list(getattr(self, '_debug', []))

    def set_status(self, text: str):
        try:
            self._status = text if text is not None else ''
        except Exception:
            pass

    def get_status(self) -> str:
        return getattr(self, '_status', '')


if PYSIDE:
    class AIPanel(QWidget):
        ask = Signal(str)
        run_task = Signal(dict)
        model_selected = Signal(str)

        def __new__(cls, *args, **kwargs):
            # If Qt is importable but no QApplication instance exists
            # (common in headless test runs), return a headless panel
            # instance to avoid Qt-related crashes.
            try:
                from PySide6.QtCore import QCoreApplication
                if QCoreApplication.instance() is None:
                    return HeadlessAIPanel()
            except Exception:
                pass
            return super().__new__(cls)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.layout = QVBoxLayout()
            # Title label to indicate provider / panel purpose
            self.title_label = QLabel('AI')
            try:
                self.title_label.setStyleSheet('font-weight: bold;')
            except Exception:
                pass
            # Title row (label + optional model selector)
            self.title_row = QHBoxLayout()
            self.title_row.addWidget(self.title_label)
            # Model selector (hidden unless this panel is for Ollama)
            try:
                self.model_combo = QComboBox()
                self.model_combo.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
                self.model_combo.hide()
                self.title_row.addWidget(self.model_combo)
            except Exception:
                self.model_combo = None

            self.layout.addLayout(self.title_row)
            self.history = QTextEdit()
            self.history.setReadOnly(True)
            self.input = QLineEdit()
            # Status label shows current assistant status (e.g. Thinking...)
            self.status_label = QLabel('')
            self.btn_row = QHBoxLayout()
            self.btn_ask = QPushButton('Ask')
            self.btn_clear = QPushButton('Clear')
            self.btn_row.addWidget(self.btn_ask)
            # Pop-out button to detach the panel into its own window
            try:
                self.btn_popout = QPushButton('Pop Out')
                self.btn_popout.setCheckable(True)
                self.btn_row.addWidget(self.btn_popout)
            except Exception:
                self.btn_popout = None
            self.btn_row.addWidget(self.btn_clear)
            self.layout.addWidget(self.history)
            self.layout.addWidget(self.input)
            self.layout.addWidget(self.status_label)
            self.layout.addLayout(self.btn_row)
            self.setLayout(self.layout)
            # No enforced minimum sizes; sizing controlled by layout only.

        def set_provider_label(self, provider_name: Optional[str]):
            try:
                if provider_name:
                    self.title_label.setText(f"AI — {provider_name}")
                else:
                    self.title_label.setText('AI')
            except Exception:
                pass
            try:
                self.provider_name = provider_name
            except Exception:
                pass

            self.btn_ask.clicked.connect(self._on_ask)
            # Allow pressing Enter in the input to send the message
            try:
                self.input.returnPressed.connect(self._on_ask)
            except Exception:
                pass
            # wire buttons
            self.btn_clear.clicked.connect(self.clear)

            try:
                if getattr(self, 'btn_popout', None):
                    self.btn_popout.clicked.connect(self._toggle_popout)
            except Exception:
                pass
            try:
                if getattr(self, 'model_combo', None):
                    self.model_combo.currentIndexChanged.connect(self._on_model_combo_changed)
            except Exception:
                pass

            # Debug file auto-refresh state
            self._debug_file_path = None
            self._debug_file_pos = 0
            self._debug_watcher = None
            self._debug_refresh_scheduled = False
            # Pop-out state
            self._popped_out = False
            self._popout_window = None
            self._dock_splitter = None
            self._dock_index = None

        def _on_ask(self):
            text = self.input.text().strip()
            if not text:
                return
            # Use append_message to keep history format consistent
            try:
                self.append_message('user', text)
            except Exception:
                try:
                    self.history.append(f"[user] {text}")
                except Exception:
                    pass
            # Log prompt to global debug (best-effort)
            try:
                from bettercopilot.logging import global_debug
                try:
                    global_debug.write({'ts': time.time(), 'event': 'user_prompt', 'provider': getattr(self, 'provider_name', None), 'text': text})
                except Exception:
                    pass
            except Exception:
                pass
            self.ask.emit(text)
            self.input.clear()
        

        def append_message(self, role: str, text: str):
            try:
                self.history.append(f"[{role}] {text}")
            except Exception:
                try:
                    # fallback to set plain text
                    self.history.insertPlainText(f"[{role}] {text}\n")
                except Exception:
                    pass
            # Ensure the new text is visible (scroll to bottom and repaint)
            try:
                from PySide6.QtGui import QTextCursor
                try:
                    self.history.moveCursor(QTextCursor.End)
                except Exception:
                    pass
                try:
                    self.history.ensureCursorVisible()
                except Exception:
                    pass
                try:
                    self.history.repaint()
                except Exception:
                    pass
            except Exception:
                pass
            # Console diagnostics for troubleshooting (visible in launcher terminal)
            try:
                print(f"[AIPanel GUI] append_message role={role} len={0 if text is None else len(str(text))}")
            except Exception:
                pass
            # Also write assistant messages to the compact debug log for troubleshooting
            try:
                if role == 'assistant':
                    try:
                        import json, time
                        dbg = {'ts': time.time(), 'event': 'assistant_append', 'text': text}
                        # include provider label when available so panels can filter
                        try:
                            if getattr(self, 'provider_name', None):
                                dbg['provider'] = getattr(self, 'provider_name')
                        except Exception:
                            pass
                        try:
                            from bettercopilot.logging import global_debug
                            try:
                                global_debug.write(dbg)
                            except Exception:
                                # fall back to class writer
                                try:
                                    s = json.dumps(dbg, ensure_ascii=False)
                                    self._write_debug_line(s)
                                except Exception:
                                    pass
                        except Exception:
                            try:
                                s = json.dumps(dbg, ensure_ascii=False)
                                self._write_debug_line(s)
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

        def update_last_message(self, role: str, text: str):
            """Replace the last message with `role` if present, otherwise append."""
            try:
                full = self.history.toPlainText()
                lines = full.splitlines()
                marker = f"[{role}]"
                idx = None
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].startswith(marker):
                        idx = i
                        break
                if idx is None:
                    # nothing to replace — append instead
                    return self.append_message(role, text)
                # replace from idx onwards with a single role line
                new_lines = lines[:idx] + [f"{marker} {text}"]
                new_text = "\n".join(new_lines)
                try:
                    self.history.setPlainText(new_text)
                except Exception:
                    try:
                        # fallback: clear + append
                        self.history.clear()
                        self.history.append(new_text)
                    except Exception:
                        pass
                try:
                    from PySide6.QtGui import QTextCursor
                    self.history.moveCursor(QTextCursor.End)
                    self.history.ensureCursorVisible()
                    try:
                        # Force a repaint so streaming updates show immediately
                        try:
                            self.history.repaint()
                        except Exception:
                            pass
                        try:
                            # Process pending Qt events to flush the UI update
                            QCoreApplication.processEvents()
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                try:
                    self.append_message(role, text)
                except Exception:
                    pass

        def _toggle_popout(self):
            # Lightweight pop-out / dock behavior. Keep logic simple to avoid
            # nested try/except mismatches and ensure reparenting is robust.
            if not PYSIDE:
                return

            if not getattr(self, '_popped_out', False):
                # discover splitter parent and index
                parent = self.parent()
                splitter = None
                try:
                    while parent is not None:
                        if isinstance(parent, QSplitter):
                            splitter = parent
                            break
                        parent = parent.parent()
                except Exception:
                    splitter = None

                if splitter is not None:
                    self._dock_splitter = splitter
                    try:
                        for i in range(splitter.count()):
                            try:
                                if splitter.widget(i) is self:
                                    self._dock_index = i
                                    break
                            except Exception:
                                pass
                    except Exception:
                        self._dock_index = None

                # detach into a new window
                try:
                    self.setParent(None)
                except Exception:
                    pass
                try:
                    win = QMainWindow()
                    win.setCentralWidget(self)
                    self._popout_window = win
                    self._popped_out = True
                    try:
                        win.show()
                    except Exception:
                        pass
                    try:
                        if getattr(self, 'btn_popout', None):
                            self.btn_popout.setText('Dock')
                            self.btn_popout.setChecked(True)
                    except Exception:
                        pass
                except Exception:
                    # best-effort fallback: leave panel as-is
                    pass
            else:
                # dock back into splitter
                try:
                    win = self._popout_window
                    if win:
                        try:
                            win.setCentralWidget(None)
                        except Exception:
                            pass
                        try:
                            win.close()
                        except Exception:
                            pass
                    if isinstance(self._dock_splitter, QSplitter) and self._dock_index is not None:
                        try:
                            self._dock_splitter.insertWidget(self._dock_index, self)
                        except Exception:
                            try:
                                self._dock_splitter.addWidget(self)
                            except Exception:
                                pass
                    else:
                        try:
                            self.setParent(None)
                        except Exception:
                            pass
                    self._popped_out = False
                    self._popout_window = None
                    try:
                        if getattr(self, 'btn_popout', None):
                            self.btn_popout.setText('Pop Out')
                            self.btn_popout.setChecked(False)
                    except Exception:
                        pass

                # close outer try block for docking fallback
                except Exception:
                    pass

        def _on_model_combo_changed(self, idx: int):
            try:
                if not getattr(self, 'model_combo', None):
                    return
                if idx is None or idx < 0:
                    return
                try:
                    model = self.model_combo.itemData(idx)
                    if model is None:
                        model = self.model_combo.currentText()
                except Exception:
                    model = self.model_combo.currentText()
                try:
                    # emit signal so API can update provider configuration
                    try:
                        self.model_selected.emit(model)
                    except Exception:
                        # fallback: no signal connected
                        pass
                except Exception:
                    pass

            except Exception:
                pass

        def set_model_list(self, models: List[str], selected: Optional[str] = None):
            try:
                if not getattr(self, 'model_combo', None):
                    return
                self.model_combo.blockSignals(True)
                try:
                    self.model_combo.clear()
                except Exception:
                    pass
                try:
                    for m in (models or []):
                        try:
                            # store model id in itemData
                            self.model_combo.addItem(str(m), m)
                        except Exception:
                            try:
                                self.model_combo.addItem(str(m))
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    if selected:
                        # try to select matching item
                        idx = -1
                        for i in range(self.model_combo.count()):
                            try:
                                if self.model_combo.itemData(i) == selected or self.model_combo.itemText(i) == selected:
                                    idx = i
                                    break
                            except Exception:
                                pass
                        if idx >= 0:
                            try:
                                self.model_combo.setCurrentIndex(idx)
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    self.model_combo.show()
                except Exception:
                    pass
                self.model_combo.blockSignals(False)
            except Exception:
                pass

        def set_selected_model(self, model: str):
            try:
                if not getattr(self, 'model_combo', None) or model is None:
                    return
                for i in range(self.model_combo.count()):
                    try:
                        if self.model_combo.itemData(i) == model or self.model_combo.itemText(i) == model:
                            self.model_combo.setCurrentIndex(i)
                            return
                    except Exception:
                        pass
            except Exception:
                pass

        def _toggle_debug(self, checked: bool):
            try:
                    # Look for debug_log.txt in several sensible locations
                    candidates = [Path.cwd()]
                    try:
                        # project root (two levels up from package file)
                        pkg_root = Path(__file__).resolve().parents[4]
                        candidates.append(pkg_root)
                    except Exception:
                        pass
                    candidates.append(Path.home())

                    logfile = None
                    for base in candidates:
                        p = Path(base) / 'debug_log.txt'
                        if p.exists():
                            logfile = p
                            break

                    if checked:
                        # Load existing file contents into the debug view (pretty-print JSON lines)
                        try:
                            self.debug_log.clear()
                            # remember chosen logfile path (may be None)
                            self._debug_file_path = logfile
                            if logfile is not None and logfile.exists():
                                with open(logfile, 'r', encoding='utf-8') as f:
                                    for line in f:
                                        ln = line.rstrip('\n')
                                        try:
                                            obj = json.loads(ln)
                                            # If this panel has a provider label, only show
                                            # debug lines that match the provider or are global
                                            prov = obj.get('provider') if isinstance(obj, dict) else None
                                            label = getattr(self, 'provider_name', None)
                                            if label and prov and prov != label:
                                                # skip entries for other providers
                                                continue
                                            pretty = json.dumps(obj, ensure_ascii=False, indent=2)
                                            self.debug_log.append(pretty)
                                            self.debug_log.append('')
                                        except Exception:
                                            self.debug_log.append(ln)
                                try:
                                    self._debug_file_pos = logfile.stat().st_size
                                except Exception:
                                    self._debug_file_pos = 0
                            else:
                                self.debug_log.append('No debug_log.txt found in:')
                                for c in candidates:
                                    self.debug_log.append(f' - {str(Path(c) / "debug_log.txt")}')
                        except Exception:
                            pass
                        self.debug_log.show()
                        self.btn_debug.setText('Hide Debug')
                        # Start watching for updates to the file or its directory
                        try:
                            self._start_debug_watcher()
                        except Exception:
                            pass
                    else:
                        # stop watching
                        try:
                            self._stop_debug_watcher()
                        except Exception:
                            pass
                        self.debug_log.hide()
                        self.btn_debug.setText('Show Debug')
            except Exception:
                pass

        def append_debug(self, text: str):
            try:
                # Delegate to global debug logger when available
                s = str(text)
                try:
                    import json
                    obj = None
                    try:
                        obj = json.loads(s)
                    except Exception:
                        obj = {'ts': time.time(), 'event': 'debug_line', 'text': s}
                        try:
                            if getattr(self, 'provider_name', None):
                                obj['provider'] = getattr(self, 'provider_name')
                        except Exception:
                            pass
                    try:
                        from bettercopilot.logging import global_debug
                        global_debug.write(obj)
                        return True
                    except Exception:
                        # fallback: write to disk via class method
                        try:
                            s2 = json.dumps(obj, ensure_ascii=False)
                            return bool(self._write_debug_line(s2))
                        except Exception:
                            return False
                except Exception:
                    pass
            except Exception:
                return False
            return False

        def _find_debug_file(self) -> Optional[Path]:
            """Return a Path to an existing debug_log.txt if found, otherwise None."""
            candidates = [Path.cwd()]
            try:
                pkg_root = Path(__file__).resolve().parents[4]
                candidates.append(pkg_root)
            except Exception:
                pass
            candidates.append(Path.home())

            for base in candidates:
                p = Path(base) / 'debug_log.txt'
                if p.exists():
                    return p
            return None

        def _start_debug_watcher(self):
            """Start a QFileSystemWatcher to auto-refresh the debug view when the file changes."""
            try:
                if not PYSIDE:
                    return
                # ensure any previous watcher is stopped
                self._stop_debug_watcher()
                watcher = QFileSystemWatcher()
                # prefer watching the file if it exists, otherwise watch cwd
                target = self._debug_file_path or (Path.cwd() / 'debug_log.txt')
                try:
                    if target.exists():
                        watcher.addPath(str(target))
                except Exception:
                    pass
                try:
                    watcher.addPath(str(target.parent))
                except Exception:
                    try:
                        watcher.addPath(str(Path.cwd()))
                    except Exception:
                        pass

                watcher.fileChanged.connect(lambda p: QTimer.singleShot(200, lambda: self._on_debug_file_changed()))
                watcher.directoryChanged.connect(lambda p: QTimer.singleShot(200, lambda: self._on_debug_file_changed()))
                self._debug_watcher = watcher
            except Exception:
                pass

        def _stop_debug_watcher(self):
            try:
                if self._debug_watcher is not None:
                    try:
                        # disconnect signals
                        self._debug_watcher.fileChanged.disconnect()
                    except Exception:
                        pass
                    try:
                        self._debug_watcher.directoryChanged.disconnect()
                    except Exception:
                        pass
                    try:
                        for p in list(self._debug_watcher.files()):
                            try:
                                self._debug_watcher.removePath(p)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        for p in list(self._debug_watcher.directories()):
                            try:
                                self._debug_watcher.removePath(p)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    self._debug_watcher = None
            except Exception:
                pass

        def _on_debug_file_changed(self):
            """Read incremental changes from the debug file and append to the debug view."""
            try:
                p = self._debug_file_path
                if p is None or not p.exists():
                    # try to locate a file now
                    p = self._find_debug_file()
                    if p is None:
                        return
                    self._debug_file_path = p
                    # read full file (pretty-print JSON lines)
                    try:
                        with open(p, 'r', encoding='utf-8') as f:
                            for line in f:
                                ln = line.rstrip('\n')
                                try:
                                    obj = json.loads(ln)
                                    pretty = json.dumps(obj, ensure_ascii=False, indent=2)
                                    self.debug_log.append(pretty)
                                    self.debug_log.append('')
                                except Exception:
                                    self.debug_log.append(ln)
                        try:
                            self._debug_file_pos = p.stat().st_size
                        except Exception:
                            self._debug_file_pos = 0
                        return
                    except Exception:
                        return

                try:
                    st = p.stat()
                    size = st.st_size
                except Exception:
                    return

                # If file shrank, reload full content
                if size < getattr(self, '_debug_file_pos', 0):
                    try:
                        with open(p, 'r', encoding='utf-8') as f:
                            for line in f:
                                ln = line.rstrip('\n')
                                try:
                                    obj = json.loads(ln)
                                    pretty = json.dumps(obj, ensure_ascii=False, indent=2)
                                    self.debug_log.append(pretty)
                                    self.debug_log.append('')
                                except Exception:
                                    self.debug_log.append(ln)
                        self._debug_file_pos = p.stat().st_size
                    except Exception:
                        pass
                    return

                if size == getattr(self, '_debug_file_pos', 0):
                    return

                # Read appended portion
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        f.seek(getattr(self, '_debug_file_pos', 0))
                        new = f.read()
                        if new:
                            for line in new.splitlines():
                                ln = line.rstrip('\n')
                                try:
                                    obj = json.loads(ln)
                                    # filter by provider label when present
                                    prov = obj.get('provider') if isinstance(obj, dict) else None
                                    label = getattr(self, 'provider_name', None)
                                    if label and prov and prov != label:
                                        continue
                                    pretty = json.dumps(obj, ensure_ascii=False, indent=2)
                                    self.debug_log.append(pretty)
                                    self.debug_log.append('')
                                except Exception:
                                    self.debug_log.append(ln)
                        self._debug_file_pos = f.tell()
                except Exception:
                    pass
            except Exception:
                pass

        def _write_debug_line(self, s: str, max_bytes: int = 5 * 1024 * 1024):
            """Write a debug line to disk, rotating the logfile when it exceeds max_bytes."""
            # Try multiple candidate locations and write to the first that succeeds.
            candidates = [Path.cwd()]
            try:
                pkg_root = Path(__file__).resolve().parents[4]
                candidates.append(pkg_root)
            except Exception:
                pass
            candidates.append(Path.home())

            written = False
            for base in candidates:
                try:
                    logfile = Path(base) / 'debug_log.txt'
                    # rotate if needed for this target
                    try:
                        b = len(s.encode('utf-8')) + 1
                        if logfile.exists() and logfile.stat().st_size + b > max_bytes:
                            rotated = logfile.with_name(f"{logfile.stem}_{time.strftime('%Y%m%d_%H%M%S')}.txt")
                            try:
                                logfile.replace(rotated)
                            except Exception:
                                try:
                                    logfile.rename(rotated)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    try:
                        logfile.parent.mkdir(parents=True, exist_ok=True)
                        with open(logfile, 'a', encoding='utf-8') as f:
                            f.write(s + "\n")
                        written = True
                        break
                    except Exception:
                        # try next candidate
                        continue
                except Exception:
                    continue

            # If nothing succeeded, silently return
            return written

        def set_status(self, text: str):
            try:
                self.status_label.setText(text if text is not None else '')
            except Exception:
                pass

        def clear(self):
            self.history.clear()

        def get_history(self) -> List[Dict]:
            try:
                text = self.history.toPlainText()
                lines = text.splitlines()
                out = []
                for ln in lines:
                    if not ln:
                        continue
                    if ln.startswith('[') and ']' in ln:
                        try:
                            idx = ln.find(']')
                            role = ln[1:idx].strip()
                            msg = ln[idx+2:] if len(ln) > idx + 2 else ''
                            out.append({'role': role, 'text': msg})
                        except Exception:
                            out.append({'role': 'assistant', 'text': ln})
                    else:
                        out.append({'role': 'assistant', 'text': ln})
                return out
            except Exception:
                return []

else:
    class AIPanel:
        def __init__(self):
            self.ask = SimpleSignal()
            self.run_task = SimpleSignal()
            self.model_selected = SimpleSignal()
            self._history = []
            self._debug = []
            self._status = ''
            self.provider_name = None
            self._models = []
            self._selected_model = None

        def append_message(self, role: str, text: str):
            try:
                self._history.append({'role': role, 'text': text})
            except Exception:
                self._history.append({'role': role, 'text': str(text)})
            # Console diagnostics for troubleshooting
            try:
                print(f"[AIPanel headless] append_message role={role} len={0 if text is None else len(str(text))}")
            except Exception:
                pass
            # Mirror assistant messages to debug log for troubleshooting
            try:
                if role == 'assistant':
                    try:
                        import json, time
                        obj = {'ts': time.time(), 'event': 'assistant_append', 'text': text}
                        try:
                            if getattr(self, 'provider_name', None):
                                obj['provider'] = getattr(self, 'provider_name')
                        except Exception:
                            pass
                        s = json.dumps(obj, ensure_ascii=False)
                        # write to debug_log.txt using same candidate locations as append_debug
                        candidates = [Path.cwd()]
                        try:
                            pkg_root = Path(__file__).resolve().parents[4]
                            candidates.append(pkg_root)
                        except Exception:
                            pass
                        candidates.append(Path.home())
                        for base in candidates:
                            try:
                                logfile = Path(base) / 'debug_log.txt'
                                logfile.parent.mkdir(parents=True, exist_ok=True)
                                with open(logfile, 'a', encoding='utf-8') as f:
                                    f.write(s + '\n')
                                break
                            except Exception:
                                continue
                    except Exception:
                        pass
            except Exception:
                pass
        def update_last_message(self, role: str, text: str):
            try:
                if len(getattr(self, '_history', [])) > 0 and self._history[-1].get('role') == role:
                    self._history[-1]['text'] = text
                else:
                    self._history.append({'role': role, 'text': text})
            except Exception:
                try:
                    self._history.append({'role': role, 'text': str(text)})
                except Exception:
                    pass

        def get_history(self) -> List[Dict]:
            return list(self._history)

        def set_provider_label(self, provider_name: Optional[str]):
            try:
                self.provider_name = provider_name
            except Exception:
                pass

        def set_model_list(self, models: List[str], selected: Optional[str] = None):
            try:
                self._models = list(models or [])
                if selected is not None:
                    self._selected_model = selected
                    try:
                        self.model_selected.emit(selected)
                    except Exception:
                        pass
            except Exception:
                pass

        def set_selected_model(self, model: str):
            try:
                self._selected_model = model
                try:
                    self.model_selected.emit(model)
                except Exception:
                    pass
            except Exception:
                pass

        def clear(self):
            self._history.clear()

        def append_debug(self, text: str):
            try:
                s = str(text)
                pretty = s
                try:
                    obj = json.loads(s)
                    # ensure provider metadata when available
                    try:
                        if getattr(self, 'provider_name', None) and not obj.get('provider'):
                            obj['provider'] = getattr(self, 'provider_name')
                    except Exception:
                        pass
                    pretty = json.dumps(obj, ensure_ascii=False, indent=2)
                except Exception:
                    pretty = s
                self._debug.append(pretty)
                try:
                    # use same rotation logic as GUI panel
                    # reuse the _write_debug_line implementation via a lightweight local copy
                    candidates = [Path.cwd()]
                    try:
                        pkg_root = Path(__file__).resolve().parents[4]
                        candidates.append(pkg_root)
                    except Exception:
                        pass
                    candidates.append(Path.home())

                    logfile = None
                    for base in candidates:
                        p = Path(base) / 'debug_log.txt'
                        if p.exists():
                            logfile = p
                            break
                    if logfile is None:
                        logfile = Path(candidates[0]) / 'debug_log.txt'

                    # rotate if necessary
                    try:
                        b = len(s.encode('utf-8')) + 1
                        max_bytes = 5 * 1024 * 1024
                        if logfile.exists() and logfile.stat().st_size + b > max_bytes:
                            rotated = logfile.with_name(f"{logfile.stem}_{time.strftime('%Y%m%d_%H%M%S')}.txt")
                            try:
                                logfile.replace(rotated)
                            except Exception:
                                try:
                                    logfile.rename(rotated)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    written = False
                    try:
                        logfile.parent.mkdir(parents=True, exist_ok=True)
                        # If original text wasn't JSON, wrap and include provider
                        try:
                            json.loads(s)
                            write_s = s
                        except Exception:
                            try:
                                wrap = {'ts': time.time(), 'event': 'debug_line', 'text': s}
                                if getattr(self, 'provider_name', None):
                                    wrap['provider'] = getattr(self, 'provider_name')
                                write_s = json.dumps(wrap, ensure_ascii=False)
                            except Exception:
                                write_s = s
                        with open(logfile, 'a', encoding='utf-8') as f:
                                f.write(write_s + "\n")
                        written = True
                    except Exception:
                        written = False
                    return written
                except Exception:
                    pass
            except Exception:
                pass
            return False

        def get_debug(self) -> List[str]:
            return list(getattr(self, '_debug', []))

        def set_status(self, text: str):
            try:
                self._status = text if text is not None else ''
            except Exception:
                pass

        def get_status(self) -> str:
            return getattr(self, '_status', '')
