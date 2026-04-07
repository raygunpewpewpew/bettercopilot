import sys
root = r'C:\Users\surfing\BetterCopilotProject\bettercopilot'
print('Inserting project root into sys.path:', root)
sys.path.insert(0, root)
print('sys.path[0]=', sys.path[0])
try:
    import PySide6
    print('PySide6 available, version:', PySide6.__version__)
except Exception as e:
    print('PySide6 import failed:', e)

try:
    import bettercopilot
    print('Imported bettercopilot package OK')
except Exception as e:
    print('Failed to import bettercopilot package:', e)

print('Done')
