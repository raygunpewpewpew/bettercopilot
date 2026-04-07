"""Script to run example MCP servers for local development."""
import subprocess
import os
import sys
from pathlib import Path


def run():
    base = Path(__file__).resolve().parents[1] / 'bettercopilot' / 'mcp' / 'servers'
    deepwiki = [sys.executable, str(base / 'deepwiki_server.py')]
    fusion = [sys.executable, str(base / 'fusion_rom_inspector.py')]
    print('Starting DeepWiki...')
    p1 = subprocess.Popen(deepwiki)
    print('Starting fusion-rom-inspector...')
    p2 = subprocess.Popen(fusion)
    try:
        p1.wait()
    except KeyboardInterrupt:
        p1.terminate()
        p2.terminate()


if __name__ == '__main__':
    run()
