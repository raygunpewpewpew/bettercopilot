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
