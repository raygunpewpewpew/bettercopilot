p='bettercopilot/ui/gui/ai_panel.py'
with open(p,'r',encoding='utf-8') as f:
    s=f.read()
print('try:', s.count('try:'))
print('except:', s.count('except:'))
print("except Exception:", s.count('except Exception:'))
print('finally:', s.count('finally:'))
# show few lines around problematic area
lines=s.splitlines()
for i in range(360,410):
    if i < len(lines):
        print(i+1, lines[i])
