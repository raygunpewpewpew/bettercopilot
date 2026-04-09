from pathlib import Path
p=Path('bettercopilot/ui/gui/ai_panel.py')
s=p.read_text()
lines=s.splitlines()
stack=[]
for i,ln in enumerate(lines):
    stripped=ln.lstrip('\t ')
    indent=len(ln)-len(stripped)
    if stripped.startswith('try:'):
        stack.append((i+1, indent))
    elif stripped.startswith('except') or stripped.startswith('finally'):
        # pop the nearest try with indent <= current
        while stack and stack[-1][1] > indent:
            stack.pop()
        if stack:
            stack.pop()
        else:
            print('Found except/finally with no matching try at line', i+1)
# After scanning
if stack:
    print('Unmatched try blocks:')
    for ln,ind in stack:
        print('  try at line', ln, 'indent', ind)
else:
    print('All try blocks matched')
