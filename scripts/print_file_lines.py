import sys
p = r'c:\Users\surfing\BetterCopilotProject\bettercopilot\bettercopilot\logging\global_debug.py'
with open(p, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, start=1):
        print(f"{i:04d}: {line.rstrip()}")
