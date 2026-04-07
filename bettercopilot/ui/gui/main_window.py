"""Main window assembling the GUI panels. Provides a headless facade when PySide6 unavailable."""
from typing import Optional

try:
    from PySide6.QtWidgets import QMainWindow, QWidget, QSplitter, QApplication, QAction, QFileDialog, QInputDialog
    from PySide6.QtCore import Qt
    PYSIDE = True
except Exception:
    PYSIDE = False

from .file_tree import FileTreePanel
from .editor import EditorPanel
from .ai_panel import AIPanel
from .diff_viewer import DiffViewer
from .status_bar import StatusBar


class HeadlessMainWindow:
    def __init__(self):
        self.file_tree = FileTreePanel()
        self.editor = EditorPanel()
        self.ai_panel = AIPanel()
        self.diff_viewer = DiffViewer()
        self.status_bar = StatusBar()

    def show(self):
        # no-op for headless
        return

    def close(self):
        return


if PYSIDE:
    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('BetterCopilot')
            self.splitter = QSplitter()
            self.file_tree = FileTreePanel()
            self.editor = EditorPanel()
            self.ai_panel = AIPanel()
            self.diff_viewer = DiffViewer()
            self.status_bar = StatusBar()

            self.splitter.addWidget(self.file_tree)
            self.splitter.addWidget(self.editor)
            self.splitter.addWidget(self.ai_panel)
            self.splitter.setStretchFactor(1, 1)

            self.setCentralWidget(self.splitter)
            self.setStatusBar(self.status_bar)

        def wiring(self, api):
            # bind frontend references to API (so API can update panels)
            if hasattr(api, 'bind_frontend'):
                try:
                    api.bind_frontend(self)
                except Exception:
                    pass

            # basic menus: File & AI
            try:
                menubar = self.menuBar()
                file_menu = menubar.addMenu('File')
                open_act = QAction('Open', self)
                open_act.triggered.connect(lambda: self._open_file_dialog(api))
                save_act = QAction('Save', self)
                save_act.triggered.connect(lambda: self.editor.save_file())
                file_menu.addAction(open_act)
                file_menu.addAction(save_act)

                ai_menu = menubar.addMenu('AI')
                ask_act = QAction('Ask...', self)
                ask_act.triggered.connect(lambda: self._ask_dialog(api))
                ai_menu.addAction(ask_act)
            except Exception:
                # if menu creation fails, continue without menus
                pass

            # connect signals to API
            self.file_tree.file_selected.connect(lambda p: api.open_file(p))
            self.ai_panel.ask.connect(lambda text: api.run_ask(text))
            self.ai_panel.fix_current_file.connect(lambda: api.run_fix(self.file_tree.current_file()))
            self.diff_viewer.apply_patch.connect(lambda patch: api.apply_patch(patch))

        def _open_file_dialog(self, api):
            try:
                fname, _ = QFileDialog.getOpenFileName(self, 'Open file', '.', 'All Files (*)')
                if fname:
                    api.open_file(fname)
            except Exception:
                if self.status_bar:
                    try:
                        self.status_bar.set_message('Open cancelled or failed')
                    except Exception:
                        pass

        def _ask_dialog(self, api):
            try:
                text, ok = QInputDialog.getText(self, 'Ask AI', 'Question:')
                if ok and text:
                    api.run_ask(text)
            except Exception:
                if self.status_bar:
                    try:
                        self.status_bar.set_message('Ask dialog failed')
                    except Exception:
                        pass

else:
    MainWindow = HeadlessMainWindow
