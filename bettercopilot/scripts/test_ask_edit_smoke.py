from bettercopilot.ui.gui.api import GUIAPI
from bettercopilot.ui.gui.main_window import HeadlessMainWindow

api = GUIAPI()
win = HeadlessMainWindow()
api.bind_frontend(win)

result = {
    'task_id': 't1',
    'final_text': '```json\n{ "chat": "Added \'banana\' to the file.", "diff": "@@ -0,0 +1 @@\\n+banana" }\n```',
    'diffs': [],
    'logs': [],
    'raw': {}
}

api._on_task_finished(result, origin='task', panel=win.ai_panel)

# inspect headless panel history and diff viewer
print('History:', win.ai_panel.get_history())
print('Diff viewer diff:', win.diff_viewer.get_diff())
