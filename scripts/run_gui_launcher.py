#!/usr/bin/env python3
"""Launcher to run the BetterCopilot GUI using the current Python interpreter.

This ensures the project root is on sys.path and calls the GUI entrypoint.
Run with: `python scripts/run_gui_launcher.py`
"""
import sys
import os
from pathlib import Path


try:
    import keyring
except Exception:
    keyring = None

if keyring:
    key = keyring.get_password('bettercopilot', 'openrouter')
    if key and not os.getenv('OPENROUTER_API_KEY'):
        os.environ['OPENROUTER_API_KEY'] = key



# Insert project root so imports resolve when running from scripts/
root = Path(__file__).parent.parent.resolve()
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Try to read OpenRouter API key from the OS credential store via `keyring`.
# This is best-effort: if `keyring` isn't available or fails, we continue silently.
try:
    import keyring
except Exception:
    keyring = None

if keyring:
    try:
        _key = keyring.get_password('bettercopilot', 'openrouter')
        if _key and not os.environ.get('OPENROUTER_API_KEY'):
            os.environ['OPENROUTER_API_KEY'] = _key
    except Exception:
        # Don't let keyring errors prevent the launcher from starting.
        pass

print('Launcher using python:', sys.executable)
print('Project root:', root)

# Run the GUI entrypoint
try:
    from bettercopilot.ui.gui.app import run_gui
except Exception:
    # fallback: try relative import for developer convenience
    from bettercopilot.ui.gui.app import run_gui

# pass through argv after script name
sys.exit(run_gui(sys.argv[1:]))
