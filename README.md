BetterCopilot
===============

BetterCopilot is a local-first, model-agnostic, tool-driven AI IDE designed as a modular Python project.

Architecture overview
- Providers: multiple interchangeable LLM backends under `bettercopilot/providers`.
- MCP tool system: JSON-RPC clients and example servers under `bettercopilot/mcp`.
- Policy layer: deterministic validators under `bettercopilot/policies`.
- Meta‑critic: generator → critic → refinement under `bettercopilot/meta_critic`.
- Orchestrator: headless task runner under `bettercopilot/orchestrator`.
- Context engine: project detection and prompt building under `bettercopilot/context`.
- UI: layered CLI and minimal TUI under `bettercopilot/ui`.

Quick start

Install dependencies (recommended in a venv):

```
python -m pip install -r requirements.txt
```

Run the CLI:

```
python -m bettercopilot.ui.cli.main ask "Hello, what can you do?"
```

Project layout

See the top-level package `bettercopilot/` for modules, and `tests/` for basic tests.

GUI Quickstart (Windows)
- Double-click `run_gui.bat` in the project root.
- Or run in a terminal:

```powershell
python scripts/run_gui_launcher.py
```

Cross-platform
- Use the Python launcher script:

```bash
python scripts/run_gui_launcher.py
```

Debugging
- `scripts/debug_run_gui_verbose.py` — prints PySide6 availability and attempts to show the main window.
- `scripts/check_qtwidgets.py` — verifies `PySide6.QtWidgets` imports.
- `scripts/find_pyside.py` and `scripts/install_pyside_all.ps1` — helper scripts to find/install PySide6 across interpreters.

See `scripts/run_gui_launcher.py` for the entrypoint that ensures the project root is on `sys.path`.

Using a real model provider (OpenRouter)
- Set your OpenRouter API key in the environment variable `OPENROUTER_API_KEY` before launching the GUI to use OpenRouter as the default provider.
	- PowerShell example:

```powershell
$env:OPENROUTER_API_KEY = 'sk-...'
python scripts/run_gui_launcher.py
```

- You can also set the `OPENROUTER_MODEL` environment variable to pick a specific model name supported by your OpenRouter plan.
