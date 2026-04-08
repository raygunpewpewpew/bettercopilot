"""Generator: produces initial outputs using providers."""
from typing import Any, Dict, List, Optional


class Generator:
    def __init__(self, provider):
        self.provider = provider

    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, system: Optional[str] = None, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        # Pass through an optional progress_callback to providers so they
        # can emit streaming or interim events back to the orchestrator/UI.
        return self.provider.generate(messages, tools=tools, system=system, progress_callback=progress_callback)
