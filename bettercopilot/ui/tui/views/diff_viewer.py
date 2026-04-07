"""TUI view: diff viewer (console fallback)."""
def show(diff_text: str = ""):
    print('\n--- Diffs ---')
    if not diff_text:
        print('(no diffs)')
        return
    print(diff_text)
