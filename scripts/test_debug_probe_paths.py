#!/usr/bin/env python3
from pathlib import Path, inspect
import bettercopilot.ui.gui.ai_panel as ap

print('cwd:', Path.cwd())
print('cwd debug exists:', (Path.cwd() / 'debug_log.txt').exists())
print('home:', Path.home())
print('home debug exists:', (Path.home() / 'debug_log.txt').exists())
print('ai_panel file:', inspect.getfile(ap))
try:
    pkg_root = Path(inspect.getfile(ap)).resolve().parents[4]
    print('pkg_root candidate:', pkg_root, (pkg_root / 'debug_log.txt').exists())
except Exception as e:
    print('pkg_root lookup failed:', e)
