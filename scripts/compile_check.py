import traceback
import sys
p = r'c:\Users\surfing\BetterCopilotProject\bettercopilot\bettercopilot\logging\global_debug.py'
try:
    with open(p, 'r', encoding='utf-8') as f:
        src = f.read()
    compile(src, p, 'exec')
    print('OK')
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
