from dataclasses import dataclass
from typing import Literal, List, Dict, Any

Role = Literal["system", "user", "assistant", "tool"]

@dataclass
class Message:
    role: Role
    content: str
    name: str | None = None
    metadata: Dict[str, Any] | None = None

Conversation = List[Message]