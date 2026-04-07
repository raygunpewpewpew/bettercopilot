#!/usr/bin/env python3
import sys, os, traceback
from pathlib import Path

root = Path(__file__).parent.parent.resolve()
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

print('Workspace root:', root)
print('Python:', sys.executable)

# 1) Provider list
try:
    from bettercopilot.ui.gui.api import _make_orchestrator
    orch = _make_orchestrator()
    provs = list(getattr(orch, 'providers', {}) .keys())
    print('providers:', provs)
except Exception as e:
    print('PROVIDER_LIST_ERROR:', e)
    traceback.print_exc()

# 2) OpenRouter smoke
try:
    from bettercopilot.providers.openrouter import OpenRouterProvider
    key = os.getenv('OPENROUTER_API_KEY')
    print('OPENROUTER_API_KEY present:' , bool(key))
    if not key:
        print('OPENROUTER_KEY_MISSING')
    else:
        try:
            prov = OpenRouterProvider(api_key=key)
            res = prov.generate([{'role':'user','content':'Hello from BetterCopilot smoke test. Say a short greeting.'}])
            print('OPENROUTER_SMOKE_OK')
            print('TEXT:', res.get('text'))
        except Exception as e:
            print('OPENROUTER_INIT_OR_CALL_ERROR:', e)
            traceback.print_exc()
except Exception as e:
    print('OPENROUTER_IMPORT_ERROR:', e)
    traceback.print_exc()

# 3) Manual provider call (explicit)
try:
    import os
    from bettercopilot.providers.openrouter import OpenRouterProvider as ORProv
    key = os.getenv('OPENROUTER_API_KEY')
    if key:
        try:
            prov = ORProv(api_key=key)
            r = prov.generate([{'role':'user','content':'Hello from test'}])
            print('MANUAL_CALL_TEXT:', r.get('text'))
            print('MANUAL_CALL_RAW_KEYS:', list((r.get('raw') or {}).keys()))
        except Exception as e:
            print('MANUAL_CALL_ERROR:', e)
            traceback.print_exc()
    else:
        print('MANUAL_CALL_SKIPPED_NO_KEY')
except Exception as e:
    print('MANUAL_CALL_IMPORT_ERROR:', e)
    traceback.print_exc()

# 4) Debug log tail
p = Path('debug_log.txt')
if not p.exists():
    print('NO_DEBUG_LOG')
else:
    print('---DEBUG_LOG_TAIL---')
    try:
        lines = p.read_text(encoding='utf-8').splitlines()
        for l in lines[-200:]:
            print(l)
    except Exception as e:
        print('DEBUG_LOG_READ_ERROR:', e)
        traceback.print_exc()
