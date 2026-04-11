"""File tree panel for GUI (PySide6 when available, headless fallback).

Exposes signals: file_selected(path), ai_fix(path), ai_explain(path), ai_rom(path)
"""
import os
from typing import List

try:
    from PySide6.QtWidgets import QWidget, QTreeView, QFileSystemModel, QMenu
    from PySide6.QtCore import Signal, QModelIndex, Slot
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
    class FileTreePanel(QWidget):
        file_selected = Signal(str)
        ai_fix = Signal(str)
        ai_explain = Signal(str)
        ai_rom = Signal(str)

        def __new__(cls, *args, **kwargs):
            try:
                from PySide6.QtCore import QCoreApplication
                if QCoreApplication.instance() is None:
                    # QCoreApplication not running -> return a lightweight headless fallback
                    class _Headless:
                        def __init__(self, root: str = '.'):
                            self.root = root
                            self.file_selected = SimpleSignal()
                            self.ai_fix = SimpleSignal()
                            self.ai_explain = SimpleSignal()
                            self.ai_rom = SimpleSignal()
                            self._current_file = None

                        def list_files(self, limit: int = 100) -> List[str]:
                            out = []
                            for dirpath, dirnames, filenames in os.walk(self.root):
                                for fn in filenames:
                                    out.append(os.path.join(dirpath, fn))
                                    if len(out) >= limit:
                                        return out
                            return out

                        def select_file(self, path: str):
                            self._current_file = path
                            try:
                                self.file_selected.emit(path)
                            except Exception:
                                # SimpleSignal will handle emitting
                                pass

                        def trigger_ai_fix(self, path: str):
                            self.ai_fix.emit(path)

                        def trigger_ai_explain(self, path: str):
                            self.ai_explain.emit(path)

                        def trigger_ai_rom(self, path: str):
                            self.ai_rom.emit(path)

                        def current_file(self) -> str:
                            return self._current_file

                    return _Headless(*args, **kwargs)
            except Exception:
                pass
            return super().__new__(cls)

        def __init__(self, root: str = '.'):
            super().__init__()
            self.root = root
            self.model = QFileSystemModel()
            self.model.setRootPath(root)
            self.view = QTreeView(self)
            self.view.setModel(self.model)
            self.view.setRootIndex(self.model.index(root))
            self._current_file = None
            self.view.clicked.connect(self._on_clicked)

        def _on_clicked(self, index: QModelIndex):
            path = self.model.filePath(index)
            self._current_file = path
            self.file_selected.emit(path)

        def select_file(self, path: str):
            # find index and select
            idx = self.model.index(path)
            if idx.isValid():
                self.view.setCurrentIndex(idx)
                self._current_file = path
                self.file_selected.emit(path)

        def current_file(self) -> str:
            return self._current_file
else:
    class FileTreePanel:
        def __init__(self, root: str = '.'):
            self.root = root
            self.file_selected = SimpleSignal()
            self.ai_fix = SimpleSignal()
            self.ai_explain = SimpleSignal()
            self.ai_rom = SimpleSignal()
            self._current_file = None

        def list_files(self, limit: int = 100) -> List[str]:
            out = []
            for dirpath, dirnames, filenames in os.walk(self.root):
                for fn in filenames:
                    out.append(os.path.join(dirpath, fn))
                    if len(out) >= limit:
                        return out
            return out

        def select_file(self, path: str):
            # emit selection
            self._current_file = path
            self.file_selected.emit(path)

        def trigger_ai_fix(self, path: str):
            self.ai_fix.emit(path)

        def trigger_ai_explain(self, path: str):
            self.ai_explain.emit(path)

        def trigger_ai_rom(self, path: str):
            self.ai_rom.emit(path)

        def current_file(self) -> str:
            return self._current_file
