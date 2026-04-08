#!/usr/bin/env python3
"""Launcher to run the BetterCopilot GUI using the current Python interpreter.

This ensures the project root is on sys.path and calls the GUI entrypoint.
Run with: `python scripts/run_gui_launcher.py`
"""
import sys
import os
from pathlib import Path
import time
import json
import uuid


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

# Rotate any existing debug_log.txt files from previous runs to avoid
# mixing stale logs with this session's debug output. We search the same
# candidate locations used by the GUI when writing logs and rotate any
# found files, then write a short session_start marker to a fresh log.
try:
    session_id = str(uuid.uuid4())
    candidates = [Path.cwd()]
    try:
        pkg_root = Path(__file__).resolve().parents[4]
        candidates.append(pkg_root)
    except Exception:
        pass
    candidates.append(Path.home())

    ts = time.strftime('%Y%m%d_%H%M%S')
    for base in candidates:
        try:
            logfile = Path(base) / 'debug_log.txt'
            if logfile.exists():
                try:
                    rotated = logfile.with_name(f"{logfile.stem}_{ts}.txt")
                    logfile.replace(rotated)
                except Exception:
                    try:
                        logfile.rename(rotated)
                    except Exception:
                        pass
        except Exception:
            pass

    # Create a new debug log at cwd and write a session marker
    try:
        target = Path(candidates[0]) / 'debug_log.txt'
        target.parent.mkdir(parents=True, exist_ok=True)
        marker = {'ts': time.time(), 'event': 'session_start', 'session_id': session_id, 'pid': os.getpid(), 'argv': sys.argv}
        with open(target, 'a', encoding='utf-8') as f:
            f.write(json.dumps(marker, ensure_ascii=False) + '\n')
        print('Debug log rotated; session id:', session_id, 'logfile:', str(target))
    except Exception:
        pass
except Exception:
    pass

# Run the GUI entrypoint
try:
    from bettercopilot.ui.gui.app import run_gui
except Exception:
    # fallback: try relative import for developer convenience
    from bettercopilot.ui.gui.app import run_gui

# pass through argv after script name
sys.exit(run_gui(sys.argv[1:]))
