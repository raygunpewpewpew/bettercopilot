# run_gui.py
from bettercopilot.ui.gui.app import run_gui
try:
    # ensure initial startup is recorded for diagnostics when launched
    from bettercopilot.logging import global_debug
    try:
        global_debug.write({'ts': __import__('time').time(), 'event': 'launcher_invoked', 'script': 'run_gui.py'})
    except Exception:
        pass
except Exception:
    pass

if __name__ == "__main__":
    run_gui()