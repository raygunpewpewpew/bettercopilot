"""Generator: produces initial outputs using providers."""
from typing import Any, Dict, List, Optional


class Generator:
    def __init__(self, provider):
        self.provider = provider

    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, system: Optional[str] = None) -> Dict[str, Any]:
        return self.provider.generate(messages, tools=tools, system=system)
