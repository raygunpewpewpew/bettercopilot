"""Provider base class and utilities.

Providers follow a simple interface that accepts OpenAI-style messages and
optionally tool schemas. Implementations should return a structured dict with
at least a `text` field and optional `tool_call` information.
"""
from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional


class Provider(ABC):
    """Abstract provider interface.

    Implementations should be interchangeable and accept messages in the
    OpenAI-style format: a list of dicts like {"role": "user", "content": "..."}.
    """

    def __init__(self, name: Optional[str] = None, logger: Optional[logging.Logger] = None):
        self.name = name or self.__class__.__name__
        self.logger = logger or logging.getLogger(self.name)

    @abstractmethod
    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, system: Optional[str] = None) -> Dict[str, Any]:
        """Generate a response.

        Returns a dict with keys such as `text`, `tool_call`, and `raw`.
        """
        raise NotImplementedError
