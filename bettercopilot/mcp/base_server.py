"""Base classes and helpers for MCP servers.

This module provides a template for implementing new MCP servers (HTTP and
stdio variants). Servers included in this repository are lightweight examples.
"""
from typing import Any, Dict
import json
import logging


class BaseMCPServer:
    """Minimal template for MCP servers."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclass to implement JSON-RPC handling.

        Accepts a parsed JSON-RPC dict and returns a response dict.
        """
        return {"jsonrpc": "2.0", "result": {"ok": True}, "id": request.get("id")}
