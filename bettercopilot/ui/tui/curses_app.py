"""Minimal curses-based TUI with headless mode for tests.

Supports tab-switching between panels, basic keybindings, and a status bar.
When `headless=True`, the app runs without curses and prints simulated UI
state for automated tests.
"""
from typing import Optional, List
import time


def run(headless: bool = True, context: Optional[dict] = None, conversation_log: Optional[List[dict]] = None, diffs: Optional[List[str]] = None):
    # Headless mode prints a simplified representation (useful for tests)
    if headless:
        print("[TUI headless] Starting BetterCopilot TUI (headless)")
        from .views import project_browser, conversation, diff_viewer
        project_browser.show(context or {})
        conversation.show(conversation_log or [])
        if diffs:
            diff_viewer.show('\n\n'.join(diffs))
        # Simulate keybindings summary
        print('\nKeybindings: TAB switch, Enter run, a:ask, f:fix, d:diff')
        return {"panels": ["project", "conversation", "diffs"], "status": {"provider": "ollama_local", "project_type": context.get('project_type') if context else 'unknown'}}

    # Real curses-based UI (minimal placeholder)
    try:
        import curses

        def _main(stdscr):
            curses.curs_set(0)
            h, w = stdscr.getmaxyx()
            statusbar = stdscr.subwin(1, w, h - 1, 0)
            stdscr.addstr(0, 0, "BetterCopilot TUI - Press q to quit")
            stdscr.refresh()
            current = 0
            panels = ["Project", "Conversation", "Diffs"]
            while True:
                stdscr.clear()
                stdscr.addstr(0, 0, f"Panel: {panels[current]}")
                statusbar.clear()
                statusbar.addstr(0, 0, f"Provider: ollama_local | Project: {context.get('project_type') if context else 'unknown'} | Tool: -")
                statusbar.refresh()
                stdscr.refresh()
                k = stdscr.getch()
                if k == ord('q'):
                    break
                elif k == 9:  # TAB
                    current = (current + 1) % len(panels)
                elif k == ord('a'):
                    stdscr.addstr(2, 0, "Ask: (not implemented in TUI)")
                elif k == ord('f'):
                    stdscr.addstr(2, 0, "Fix: (not implemented in TUI)")
                elif k == ord('d'):
                    stdscr.addstr(2, 0, "Diffs: (not implemented in TUI)")

        curses.wrapper(_main)
    except Exception:
        print("Curses UI unavailable; run in headless mode")
        return None
