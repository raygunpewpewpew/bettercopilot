"""MCP (Model Context Protocol) tools and helpers.

This package includes a JSON-RPC client for HTTP and stdio servers, a simple
registry for locating tools, and example servers.
"""
from .client import JSONRPCClient, StdioJSONRPCClient
from .registry import MCPRegistry

__all__ = ["JSONRPCClient", "StdioJSONRPCClient", "MCPRegistry"]
