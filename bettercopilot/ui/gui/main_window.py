"""Main window assembling the GUI panels. Provides a headless facade when PySide6 unavailable."""
from typing import Optional

# Detect PySide6 availability by attempting to import the Qt modules
# and bind the commonly used classes. Some PySide6 builds expose certain
# symbols (like QAction) in QtGui instead of QtWidgets, so we import the
# modules and fall back selectively to avoid ImportError here.
try:
    from PySide6 import QtWidgets, QtCore
    Qt = QtCore.Qt
    QMainWindow = QtWidgets.QMainWindow
    QWidget = QtWidgets.QWidget
    QSplitter = QtWidgets.QSplitter
    QApplication = QtWidgets.QApplication
    QFileDialog = QtWidgets.QFileDialog
    QInputDialog = QtWidgets.QInputDialog
    QDockWidget = QtWidgets.QDockWidget
    # QAction may be in QtWidgets on some builds, or in QtGui on others
    try:
        QAction = QtWidgets.QAction
    except Exception:
        from PySide6.QtGui import QAction
    PYSIDE = True
except Exception:
    PYSIDE = False

from .file_tree import FileTreePanel
from .editor import EditorPanel
from .ai_panel import AIPanel
from .diff_viewer import DiffViewer
from .status_bar import StatusBar
from .debug_panel import DebugPanel


class HeadlessMainWindow:
    def __init__(self):
        self.file_tree = FileTreePanel()
        self.editor = EditorPanel()
        self.ai_panel = AIPanel()
        try:
            self.ai_panel.set_provider_label('OpenRouter')
        except Exception:
            pass
        self.ai_panel_ollama = AIPanel()
        try:
            self.ai_panel_ollama.set_provider_label('Ollama')
        except Exception:
            pass
        self.diff_viewer = DiffViewer()
        self.debug_panel = DebugPanel()
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
            try:
                self.ai_panel.set_provider_label('OpenRouter')
            except Exception:
                pass
            self.ai_panel_ollama = AIPanel()
            try:
                self.ai_panel_ollama.set_provider_label('Ollama')
            except Exception:
                pass
            self.diff_viewer = DiffViewer()
            self.debug_panel = DebugPanel()
            self.status_bar = StatusBar()

            # Add panels to the main splitter so each is resizable by the user.
            # Place file tree and debug panel in a vertical container so the
            # debug field appears directly under the file tree as requested.
            try:
                left_container = QWidget()
                left_layout = QtWidgets.QVBoxLayout()
                left_layout.setContentsMargins(0, 0, 0, 0)
                left_layout.addWidget(self.file_tree)
                try:
                    left_layout.addWidget(self.debug_panel)
                except Exception:
                    pass
                left_container.setLayout(left_layout)
                self.splitter.addWidget(left_container)
            except Exception:
                # fallback: add file_tree directly
                try:
                    self.splitter.addWidget(self.file_tree)
                except Exception:
                    pass
            self.splitter.addWidget(self.editor)
            # Group the two AI panels into a right-hand container so they
            # remain side-by-side and are restored together by the main splitter.
            try:
                self.ai_container = QSplitter()
                try:
                    self.ai_container.setOrientation(Qt.Horizontal)
                except Exception:
                    pass
                self.ai_container.addWidget(self.ai_panel)
                self.ai_container.addWidget(self.ai_panel_ollama)
                self.splitter.addWidget(self.ai_container)
            except Exception:
                # fallback: add panels individually
                try:
                    self.splitter.addWidget(self.ai_panel)
                except Exception:
                    pass
                try:
                    self.splitter.addWidget(self.ai_panel_ollama)
                except Exception:
                    pass

            # Prefer the editor to take most space by default while still
            # allowing the file tree and AI panel container to be resized by the user.
            # No explicit stretch factors: allow the user to resize without
            # programmatic relative sizing constraints.

            # Place the splitter in a vertical container so we can reserve
            # ~10% of the central area as margins and give the splitter
            # ~90% of the central widget height by default.
            container = QWidget()
            vbox = QtWidgets.QVBoxLayout()
            vbox.setContentsMargins(0, 0, 0, 0)
            # Simply place the splitter in the layout without explicit stretch values.
            vbox.addWidget(self.splitter)
            container.setLayout(vbox)
            self.setCentralWidget(container)
            self.setStatusBar(self.status_bar)

            # Create a dock for the diff viewer so it can be moved/resized
            try:
                self.diff_dock = QDockWidget('Diff Viewer', self)
                self.diff_dock.setWidget(self.diff_viewer)
                self.diff_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
                self.diff_dock.setObjectName('diffViewerDock')
                self.addDockWidget(Qt.RightDockWidgetArea, self.diff_dock)
                # hide diff viewer by default; restoreState() will show it if previously visible
                try:
                    self.diff_dock.hide()
                except Exception:
                    pass
            except Exception:
                self.diff_dock = None

            # Add 1px black borders to main panels/containers for clarity
            try:
                try:
                    self.file_tree.setStyleSheet('border: 1px solid black;')
                except Exception:
                    pass
                try:
                    self.editor.setStyleSheet('border: 1px solid black;')
                except Exception:
                    pass
                try:
                    self.ai_panel.setStyleSheet('border: 1px solid black;')
                except Exception:
                    pass
                try:
                    self.ai_panel_ollama.setStyleSheet('border: 1px solid black;')
                except Exception:
                    pass
                try:
                    if getattr(self, 'ai_container', None):
                        self.ai_container.setStyleSheet('border: 1px solid black;')
                except Exception:
                    pass
                try:
                    self.diff_viewer.setStyleSheet('border: 1px solid black;')
                except Exception:
                    pass
                try:
                    self.status_bar.setStyleSheet('border: 1px solid black;')
                except Exception:
                    pass
            except Exception:
                pass

            # Persist and restore window geometry and state between runs.
            try:
                settings = QtCore.QSettings('BetterCopilot', 'BetterCopilot')
                # Restore window state (dock widgets etc.) if available
                try:
                    state = settings.value('mainWindow/state')
                    if state:
                        try:
                            self.restoreState(state)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Restore geometry if present
                try:
                    geom = settings.value('mainWindow/geometry')
                    if geom:
                        try:
                            self.restoreGeometry(geom)
                        except Exception:
                            pass
                except Exception:
                    pass

                maximized = settings.value('mainWindow/maximized')
                if maximized is None:
                    try:
                        self.showMaximized()
                    except Exception:
                        pass
                else:
                    try:
                        if str(maximized).lower() in ('1', 'true'):
                            self.showMaximized()
                    except Exception:
                        pass
            except Exception:
                # Do not let settings failures break startup
                pass

            # No automatic splitter size corrections to avoid absolute/relative sizing.

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
                # Settings menu with autosave toggle
                settings_menu = menubar.addMenu('Settings')
                autosave_act = QAction('Autosave patches', self)
                autosave_act.setCheckable(True)
                try:
                    if hasattr(api, 'autosave'):
                        autosave_act.setChecked(bool(api.autosave))
                except Exception:
                    pass

                def _set_autosave(checked):
                    try:
                        if hasattr(api, 'set_autosave'):
                            api.set_autosave(bool(checked))
                        else:
                            api.autosave = bool(checked)
                    except Exception:
                        pass

                autosave_act.toggled.connect(_set_autosave)
                settings_menu.addAction(autosave_act)
                # Direct provider chat toggle
                try:
                    direct_chat_act = QAction('Direct Provider Chat', self)
                    direct_chat_act.setCheckable(True)
                    try:
                        if hasattr(api, 'get_direct_chat'):
                            direct_chat_act.setChecked(bool(api.get_direct_chat()))
                    except Exception:
                        pass

                    def _set_direct_chat(checked):
                        try:
                            if hasattr(api, 'set_direct_chat'):
                                api.set_direct_chat(bool(checked))
                        except Exception:
                            pass

                    direct_chat_act.toggled.connect(_set_direct_chat)
                    settings_menu.addAction(direct_chat_act)
                except Exception:
                    pass
            except Exception:
                # if menu creation fails, continue without menus
                pass

            # Add a View menu to toggle docked panels
            try:
                view_menu = menubar.addMenu('View')
                # Diff viewer toggle
                try:
                    diff_act = QAction('Diff Viewer', self)
                    diff_act.setCheckable(True)
                    diff_act.setChecked(bool(self.diff_dock and self.diff_dock.isVisible()))
                    diff_act.toggled.connect(lambda checked: self.diff_dock.setVisible(checked) if self.diff_dock else None)
                    # Keep action in sync if the dock visibility changes
                    try:
                        if self.diff_dock is not None and hasattr(self.diff_dock, 'visibilityChanged'):
                            self.diff_dock.visibilityChanged.connect(lambda v: diff_act.setChecked(bool(v)))
                    except Exception:
                        pass
                    view_menu.addAction(diff_act)
                except Exception:
                    pass

                # add Reset Layout under Settings menu if available
                try:
                    reset_act = QAction('Reset Layout', self)
                    reset_act.triggered.connect(lambda: self.reset_layout())
                    settings_menu.addAction(reset_act)
                except Exception:
                    pass
            except Exception:
                pass

            # connect signals to API
            self.file_tree.file_selected.connect(lambda p: api.open_file(p))

            # use the instance helper to include editor content with prompts

            # Primary AI panel -> OpenRouter: always include editor content
            try:
                self.ai_panel.ask.connect(lambda text: api.run_ask(self._make_goal_with_editor(text), provider_override='openrouter', response_panel=self.ai_panel))
            except Exception:
                try:
                    self.ai_panel.ask.connect(lambda text: api.run_ask(self._make_goal_with_editor(text)))
                except Exception:
                    pass

            # Secondary AI panel -> Ollama: always include editor content
            try:
                self.ai_panel_ollama.ask.connect(lambda text: api.run_ask(self._make_goal_with_editor(text), provider_override='ollama', response_panel=self.ai_panel_ollama))
            except Exception:
                try:
                    self.ai_panel_ollama.ask.connect(lambda text: api.run_ask(self._make_goal_with_editor(text)))
                except Exception:
                    pass

            self.diff_viewer.apply_patch.connect(lambda patch: api.apply_patch(patch))

        def _make_goal_with_editor(self, text):
            try:
                editor_text = self.editor.get_text() if hasattr(self, 'editor') else ''
            except Exception:
                editor_text = ''

            # If the user is explicitly asking to create a *new script*, do
            # not include current editor contents — send an empty editor field
            # so the provider can generate a fresh file.
            try:
                txt = (text or '').lower()
                new_script_keywords = ['write a new script', 'create a new script', 'generate a script', 'new script', 'write script', 'create script', 'generate a script']
                if any(k in txt for k in new_script_keywords):
                    editor_text = ''
            except Exception:
                pass

            goal = (
                "Editor content:\n" + (editor_text or "") + "\n\nUser prompt:\n" + (text or "")
            )
            return goal

        def show(self):
            # Ensure the window is shown, raised, activated, and centered on the
            # primary screen. Guard all calls to avoid exceptions when running
            # in unusual environments or tests.
            try:
                super().show()
            except Exception:
                try:
                    QMainWindow.show(self)
                except Exception:
                    pass

            try:
                # bring to front
                try:
                    self.raise_()
                    self.activateWindow()
                except Exception:
                    pass

                # center on primary screen if available
                try:
                    screen = None
                    # prefer the window's screen if available
                    if hasattr(self, 'screen'):
                        try:
                            screen = self.screen()
                        except Exception:
                            screen = None

                    if screen is None:
                        try:
                            screen = QApplication.primaryScreen()
                        except Exception:
                            screen = None

                    if screen:
                        # Don't adjust position if the window is maximized
                        try:
                            if self.isMaximized():
                                return
                        except Exception:
                            pass

                        geom = self.geometry()
                        sgeom = screen.availableGeometry()
                        cx = sgeom.x() + (sgeom.width() - geom.width()) // 2
                        cy = sgeom.y() + (sgeom.height() - geom.height()) // 2
                        try:
                            self.move(cx, cy)
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                pass

        def closeEvent(self, event):
            # Save geometry, window state and splitter sizes so the layout is restored next run
            try:
                settings = QtCore.QSettings('BetterCopilot', 'BetterCopilot')
                try:
                    settings.setValue('mainWindow/geometry', self.saveGeometry())
                except Exception:
                    pass
                try:
                    settings.setValue('mainWindow/maximized', self.isMaximized())
                except Exception:
                    pass
                try:
                    # Save QMainWindow state (dock widget positions)
                    settings.setValue('mainWindow/state', self.saveState())
                except Exception:
                    pass
                try:
                    settings.setValue('mainWindow/splitterSizes', self.splitter.sizes())
                except Exception:
                    pass
            except Exception:
                pass
            try:
                super().closeEvent(event)
            except Exception:
                event.accept()

        def reset_layout(self):
            try:
                settings = QtCore.QSettings('BetterCopilot', 'BetterCopilot')
                try:
                    # remove saved mainWindow keys
                    settings.remove('mainWindow')
                except Exception:
                    pass
            except Exception:
                pass
            # Do not set absolute or relative sizes; simply ensure diff dock visible
            try:
                if getattr(self, 'diff_dock', None):
                    try:
                        self.diff_dock.show()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                if getattr(self, 'diff_dock', None) is not None:
                    try:
                        self.diff_dock.show()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                self.showMaximized()
            except Exception:
                pass

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
                    try:
                        api.run_ask(self._make_goal_with_editor(text), response_panel=self.ai_panel)
                    except Exception:
                        api.run_ask(self._make_goal_with_editor(text))
            except Exception:
                if self.status_bar:
                    try:
                        self.status_bar.set_message('Ask dialog failed')
                    except Exception:
                        pass

else:
    MainWindow = HeadlessMainWindow
