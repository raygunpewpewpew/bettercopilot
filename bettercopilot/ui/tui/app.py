"""Minimal TUI application (placeholder).

Provides simple console views for project browsing, conversation and diffs.
This is intentionally minimal — a real TUI would use curses or textual.
"""
from .views import project_browser, conversation, diff_viewer


def run(context=None, conversation_log=None, diffs=None):
    print("=== BetterCopilot TUI (minimal) ===")
    project_browser.show(context)
    conversation.show(conversation_log or [])
    if diffs:
        diff_viewer.show('\n\n'.join(diffs))
