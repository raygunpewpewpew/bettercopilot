import ast, sys
p = r'c:\Users\surfing\BetterCopilotProject\bettercopilot\bettercopilot\ui\gui\api.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print('OK')
except SyntaxError as e:
    print('SyntaxError:', e)
    lines = src.splitlines()
    ln = e.lineno or 0
    for i in range(max(0, ln-5), min(len(lines), ln+5)):
        print(f"{i+1:04d}: {lines[i]!r}")
    sys.exit(1)
