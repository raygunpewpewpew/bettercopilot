from bettercopilot.ui.tui.curses_app import run as tui_run


def test_tui_headless():
    res = tui_run(headless=True, context={'project_type': 'python', 'selected_files': []}, conversation_log=[{'role': 'assistant', 'content': 'hi'}], diffs=['-old +new'])
    assert isinstance(res, dict)
    assert 'panels' in res
