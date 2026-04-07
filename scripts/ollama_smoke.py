#!/usr/bin/env python3
"""Ollama smoke test: instantiate `OllamaHTTPProvider` and send a short prompt.

Prints a short status and the provider's text output (truncated).
"""
import os, sys, traceback
from pathlib import Path

# Ensure project root is on sys.path when running from the scripts/ folder
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))

try:
    from bettercopilot.providers.ollama_http import OllamaHTTPProvider
except Exception as e:
    print('IMPORT_ERROR', str(e))
    traceback.print_exc()
    sys.exit(2)

# Allow empty OLLAMA_URL (defaults to localhost) but attempt to instantiate
url = os.getenv('OLLAMA_URL')
try:
    prov = OllamaHTTPProvider(api_url=url)
except Exception as e:
    print('INIT_ERROR', str(e))
    traceback.print_exc()
    sys.exit(4)

try:
    res = prov.generate([{'role': 'user', 'content': 'Hello from BetterCopilot Ollama smoke test. Say a short greeting.'}])
    if isinstance(res, dict):
        text = res.get('text') or ''
        print('OK')
        print(text[:1000])
    else:
        print('OK')
        print(str(res)[:1000])
except Exception as e:
    print('CALL_ERROR', str(e))
    traceback.print_exc()
    sys.exit(5)
