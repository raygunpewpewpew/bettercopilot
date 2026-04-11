#!/usr/bin/env python3
"""Simple test: verify that sudoku.html contains the solved event and
an accessible, non-blocking announcement (aria-live or announcer element).

This test checks for the `sudokuSolved` event dispatch and an announcer
element or aria-live text indicating the puzzle is solved.
"""
import sys
from pathlib import Path

p = Path(__file__).resolve().parents[2] / 'sudoku.html'
print('Checking file:', p)
if not p.exists():
    print('sudoku.html not found at', p)
    sys.exit(2)

text = p.read_text(encoding='utf-8')
has_event = 'sudokuSolved' in text
has_announcer = 'sudoku-announcer' in text or 'aria-live' in text or 'Puzzle solved!' in text

if has_event and has_announcer:
    print('Found sudokuSolved event and accessible announcement')
    sys.exit(0)
else:
    print('Missing solved event/announcement. Snippet preview:')
    start = max(0, text.find('Solver finished') - 200)
    end = text.find('Solver finished') + 400 if text.find('Solver finished') != -1 else start + 600
    snippet = text[start:end]
    print(snippet)
    sys.exit(1)
