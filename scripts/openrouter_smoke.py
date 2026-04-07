#!/usr/bin/env python3
"""OpenRouter smoke test: reads OPENROUTER_API_KEY from env and sends a short prompt.
Prints a short status and the provider's text output (truncated).
"""
import os, sys, traceback
from pathlib import Path

# Ensure project root is on sys.path when running from the scripts/ folder
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))

try:
    from bettercopilot.providers.openrouter import OpenRouterProvider
except Exception as e:
    print('IMPORT_ERROR', str(e))
    traceback.print_exc()
    sys.exit(2)

key = os.getenv('OPENROUTER_API_KEY')
if not key:
    print('MISSING_KEY')
    sys.exit(3)

try:
    prov = OpenRouterProvider(api_key=key)
except Exception as e:
    print('INIT_ERROR', str(e))
    traceback.print_exc()
    sys.exit(4)

try:
    res = prov.generate([{'role':'user','content':'Hello from BetterCopilot smoke test. Say a short greeting.'}])
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
