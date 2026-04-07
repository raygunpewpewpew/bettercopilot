#!/usr/bin/env python3
import traceback
print('python:', __import__('sys').executable)
try:
    from PySide6.QtWidgets import QMainWindow, QWidget, QSplitter, QApplication, QAction, QFileDialog, QInputDialog
    from PySide6.QtCore import Qt
    print('Exact imports OK')
except Exception:
    print('Exact imports FAILED:')
    traceback.print_exc()
