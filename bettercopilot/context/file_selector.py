"""Select relevant files for a task given a project type and workspace.

Also provides small utilities to extract code snippets with line numbers.
"""
import os
from typing import List, Dict


class FileSelector:
    def __init__(self, root: str = '.'):
        self.root = root

    def select(self, project_type: str, limit: int = 10) -> List[str]:
        files = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                if project_type == 'python' and fn.endswith('.py'):
                    files.append(p)
                if project_type == 'rom' and fn.lower().endswith(('.gba', '.bin', '.ips')):
                    files.append(p)
                if project_type == 'assembly' and fn.lower().endswith(('.s', '.asm', '.inc')):
                    files.append(p)
            if len(files) >= limit:
                break
        return files[:limit]

    def extract_snippets(self, file_path: str, max_lines: int = 200) -> List[Dict]:
        """Extract up to `max_lines` of content from `file_path` with line numbers.

        Returns a list of dicts: {"start": int, "end": int, "text": str}
        """
        snippets: List[Dict] = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return snippets

        total = len(lines)
        if total == 0:
            return snippets

        # Return a single snippet containing the first `max_lines` lines
        end = min(max_lines, total)
        snippet = {"start": 1, "end": end, "text": ''.join(lines[0:end])}
        snippets.append(snippet)

        # If file larger, include last few lines as context
        if total > max_lines:
            start2 = max(1, total - max_lines + 1)
            snippets.append({"start": start2, "end": total, "text": ''.join(lines[start2 - 1:total])})

        return snippets
