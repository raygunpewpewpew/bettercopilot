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

            # Add panels to the main splitter so each is resizable by the user.
            self.splitter.addWidget(self.file_tree)
            self.splitter.addWidget(self.editor)
            self.splitter.addWidget(self.ai_panel)

            # Prefer the editor to take most space by default while still
            # allowing the file tree and AI panel to be resized by the user.
            self.splitter.setStretchFactor(0, 1)
            self.splitter.setStretchFactor(1, 4)
            self.splitter.setStretchFactor(2, 1)

            # Place the splitter in a vertical container so we can reserve
            # ~10% of the central area as margins and give the splitter
            # ~90% of the central widget height by default.
            container = QWidget()
            vbox = QtWidgets.QVBoxLayout()
            vbox.setContentsMargins(0, 0, 0, 0)
            # top margin (5%), splitter (90%), bottom margin (5%) => weights 1,18,1
            vbox.addStretch(1)
            vbox.addWidget(self.splitter, 18)
            vbox.addStretch(1)
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

            # Persist and restore window geometry + splitter sizes between runs
            try:
                settings = QtCore.QSettings('BetterCopilot', 'BetterCopilot')

                # Restore splitter sizes if present, otherwise compute sensible defaults
                try:
                    sizes = settings.value('mainWindow/splitterSizes')
                    if sizes and isinstance(sizes, (list, tuple)):
                        self.splitter.setSizes([int(x) for x in sizes])
                    else:
                        # Try to compute defaults from primary screen width
                        try:
                            screen = QApplication.primaryScreen()
                            if screen:
                                w = screen.availableGeometry().width()
                            else:
                                w = 1200
                            self.splitter.setSizes([int(w * 0.10), int(w * 0.70), int(w * 0.20)])
                        except Exception:
                            # fallback to small ratio values
                            try:
                                self.splitter.setSizes([100, 800, 200])
                            except Exception:
                                pass
                except Exception:
                    try:
                        self.splitter.setSizes([100, 800, 200])
                    except Exception:
                        pass

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
                    # No previous setting — default to maximized as requested
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
            self.ai_panel.ask.connect(lambda text: api.run_ask(text))
            self.ai_panel.fix_current_file.connect(lambda: api.run_fix(self.file_tree.current_file()))
            self.diff_viewer.apply_patch.connect(lambda patch: api.apply_patch(patch))

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
            # Apply default sizes and ensure diff dock is visible
            try:
                self.splitter.setSizes([150, 800, 150])
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
                    api.run_ask(text)
            except Exception:
                if self.status_bar:
                    try:
                        self.status_bar.set_message('Ask dialog failed')
                    except Exception:
                        pass

else:
    MainWindow = HeadlessMainWindow
