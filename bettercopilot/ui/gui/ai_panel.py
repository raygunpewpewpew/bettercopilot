"""AI panel: conversation, input, and controls. Headless fallback included."""
from typing import List, Dict, Optional
from pathlib import Path
import time
import os
import json

try:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QLabel
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
            # Status label shows current assistant status (e.g. Thinking...)
            self.status_label = QLabel('')
            self.btn_row = QHBoxLayout()
            self.btn_ask = QPushButton('Ask')
            self.btn_fix = QPushButton('Fix File')
            self.btn_run = QPushButton('Run Task')
            self.btn_clear = QPushButton('Clear')
            self.btn_row.addWidget(self.btn_ask)
            self.btn_row.addWidget(self.btn_fix)
            self.btn_row.addWidget(self.btn_run)
            # Debug toggle button (shows/hides expanded debug log)
            self.btn_debug = QPushButton('Show Debug')
            self.btn_debug.setCheckable(True)
            self.btn_row.addWidget(self.btn_debug)
            self.btn_row.addWidget(self.btn_clear)
            self.layout.addWidget(self.history)
            self.layout.addWidget(self.input)
            self.layout.addWidget(self.status_label)
            # Expanded debug log (hidden by default)
            self.debug_log = QTextEdit()
            self.debug_log.setReadOnly(True)
            self.debug_log.hide()
            # attach JSON highlighter if available
            try:
                # JsonHighlighter defined above when PYSIDE is True
                self._json_highlighter = JsonHighlighter(self.debug_log.document())
            except Exception:
                self._json_highlighter = None
            self.layout.addWidget(self.debug_log)
            self.layout.addLayout(self.btn_row)
            self.setLayout(self.layout)

            self.btn_ask.clicked.connect(self._on_ask)
            # Allow pressing Enter in the input to send the message
            try:
                self.input.returnPressed.connect(self._on_ask)
            except Exception:
                pass
            self.btn_fix.clicked.connect(lambda: self.fix_current_file.emit())
            self.btn_run.clicked.connect(lambda: self.run_task.emit({}))
            self.btn_clear.clicked.connect(self.clear)
            self.btn_debug.toggled.connect(self._toggle_debug)

            # Debug file auto-refresh state
            self._debug_file_path = None
            self._debug_file_pos = 0
            self._debug_watcher = None
            self._debug_refresh_scheduled = False

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
                        s = json.dumps(dbg, ensure_ascii=False)
                        try:
                            self._write_debug_line(s)
                        except Exception:
                            pass
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
                if hasattr(self, 'debug_log'):
                    s = str(text)
                    pretty = s
                    try:
                        obj = json.loads(s)
                        pretty = json.dumps(obj, ensure_ascii=False, indent=2)
                    except Exception:
                        pretty = s

                    try:
                        self.debug_log.append(pretty)
                        self.debug_log.append('')
                    except Exception:
                        pass

                    # Append compact original to disk with rotation
                    try:
                        written = self._write_debug_line(s)
                        return bool(written)
                    except Exception:
                        return False
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

else:
    class AIPanel:
        def __init__(self):
            self.ask = SimpleSignal()
            self.fix_current_file = SimpleSignal()
            self.run_task = SimpleSignal()
            self._history = []
            self._debug = []
            self._status = ''

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
                        s = json.dumps({'ts': time.time(), 'event': 'assistant_append', 'text': text}, ensure_ascii=False)
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

        def get_history(self) -> List[Dict]:
            return list(self._history)

        def clear(self):
            self._history.clear()

        def append_debug(self, text: str):
            try:
                s = str(text)
                pretty = s
                try:
                    obj = json.loads(s)
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
                        with open(logfile, 'a', encoding='utf-8') as f:
                            f.write(s + "\n")
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
