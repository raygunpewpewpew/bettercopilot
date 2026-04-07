"""Task model representing an AI task to run in the orchestrator."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Task:
    id: str
    goal: str
    files: List[str] = field(default_factory=list)
    provider: Optional[str] = None
    policies: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
