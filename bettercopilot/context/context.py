"""Unified Context object for orchestrator and prompt building.

Contains project metadata, selected files, tool schemas, and policy summaries.
Also exposes a small helper to compute diffs.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from difflib import unified_diff


@dataclass
class Context:
    root: str = '.'
    project_type: str = 'unknown'
    selected_files: List[str] = field(default_factory=list)
    snippets: Dict[str, List[Dict]] = field(default_factory=dict)
    tool_schemas: List[Dict] = field(default_factory=list)
    policy_summaries: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @staticmethod
    def compute_diffs(old_text: str, new_text: str) -> str:
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        return ''.join(unified_diff(old_lines, new_lines, lineterm=''))

    def to_prompt(self) -> str:
        parts = [f"Project type: {self.project_type}"]
        if self.selected_files:
            parts.append("Files: " + ", ".join(self.selected_files[:10]))
        if self.policy_summaries:
            parts.append("Policies: " + ", ".join(p['name'] for p in self.policy_summaries))
        return "\n".join(parts)
