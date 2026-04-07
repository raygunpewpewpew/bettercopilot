"""Build prompts by combining system, project, policy and tool information."""
from typing import List, Dict, Optional


class PromptBuilder:
    def __init__(self, system_template: Optional[str] = None):
        self.system_template = system_template or "You are BetterCopilot, an assistant for code and ROM tooling."

    def build(self, goal: str, selected_files: List[str] = None, policies: List[str] = None, tools: List[Dict] = None) -> List[Dict]:
        system = self.system_template
        if policies:
            system += "\nPolicies: " + ", ".join(policies)
        if tools:
            system += "\nTools available: " + ", ".join(t.get('name', str(t)) for t in tools)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": goal}
        ]
        return messages
