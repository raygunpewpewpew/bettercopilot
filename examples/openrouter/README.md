OpenRouter examples for BetterCopilotProject

This folder contains small, copyable examples showing how to call
the OpenRouter API for simple completions, structured outputs, streaming
SSE, and function/tool calling. Set `OPENROUTER_API_KEY` in your
environment before running the scripts.

Examples:
- `simple_request.py` — basic non-streaming chat completion
- `structured_outputs.py` — request JSON schema / structured output
- `streaming_sse.py` — simple SSE streaming reader (ignore SSE comments)
- `tools_example.py` — example request with `tools` / function-call shape

Usage:

```powershell
$env:OPENROUTER_API_KEY = 'sk-...'
python simple_request.py
```

These are intended as reference snippets and can be copied into your
projects or adapted to the GUI provider logic.
