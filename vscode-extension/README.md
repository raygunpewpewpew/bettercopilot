This folder contains a minimal VS Code extension scaffold that can call the
BetterCopilot Python bridge. The extension itself is intentionally thin; the
real logic runs in Python via the `vscode_bridge_server.py` script.

Files:
- `extension.js`: minimal client that posts to local HTTP bridge.
