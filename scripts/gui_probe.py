# probe GUI imports without starting QApplication
import importlib
import sys
print('PYTHON', sys.executable)
try:
    app_mod = importlib.import_module('bettercopilot.ui.gui.app')
    print('imported app_mod')
    print('app_mod.PYSIDE =', getattr(app_mod, 'PYSIDE', None))
except Exception as e:
    print('app_mod import failed:', repr(e))

try:
    import PySide6
    print('PySide6 version =', getattr(PySide6, '__version__', None))
    print('PySide6 file =', getattr(PySide6, '__file__', None))
except Exception as e:
    print('PySide6 import failed:', repr(e))

try:
    # import main_window too
    main_mod = importlib.import_module('bettercopilot.ui.gui.main_window')
    print('imported main_window')
    print('main_mod.PYSIDE =', getattr(main_mod, 'PYSIDE', None))
except Exception as e:
    print('main_window import failed:', repr(e))

print('probe done')
