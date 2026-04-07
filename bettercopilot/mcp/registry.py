"""MCP registry and routing helpers.

Simple in-memory registry for demo purposes.
"""
from typing import Dict, Optional, List
from .client import JSONRPCClient, StdioJSONRPCClient
import logging
import time


class MCPRegistry:
    """Registry of named tools to endpoints.

    For a real implementation this might query a service directory or
    use service discovery. Here we provide a simple static mapping that can
    be extended at runtime.
    """

    def __init__(self):
        # Example defaults; processes and servers can register themselves
        self._registry: Dict[str, Dict] = {
            "deepwiki": {"type": "http", "endpoint": "http://localhost:8765/"},
            "fusion-rom-inspector": {"type": "stdio", "cmd": ["python", "-u", "c:/Users/surfing/BetterCopilotProject/bettercopilot/bettercopilot/mcp/servers/fusion_rom_inspector.py"]},
        }
        # Tools map tool_name -> server_name (simple mapping)
        self._tools: Dict[str, Dict] = {
            # initial static mapping; discovery may enrich this
            "deepwiki": {"server": "deepwiki", "schema": {"methods": ["query"]}},
            "fusion_inspect": {"server": "fusion-rom-inspector", "schema": {"methods": ["inspect"]}},
        }
        self._cache_time = 0
        self.logger = logging.getLogger("MCPRegistry")

    def register(self, name: str, info: Dict):
        self._registry[name] = info

    def get(self, name: str) -> Optional[Dict]:
        return self._registry.get(name)

    def list(self):
        return dict(self._registry)

    # New helpers for tool/service mapping
    def register_server(self, server_name: str, info: Dict):
        self._registry[server_name] = info

    def register_tool(self, tool_name: str, server_name: str, schema: Dict = None):
        self._tools[tool_name] = {"server": server_name, "schema": schema or {}}

    def get_server_for_tool(self, tool_name: str) -> Optional[Dict]:
        t = self._tools.get(tool_name)
        if not t:
            return None
        server = t.get('server')
        return self._registry.get(server)

    def list_tools(self):
        return list(self._tools.keys())

    def discover_tools(self, refresh_after: float = 30.0) -> Dict[str, Dict]:
        """Query all registered servers for available tools and cache schemas.

        refresh_after: seconds to live for cached discovery results.
        Returns a mapping tool_name -> schema dict.
        """
        now = time.time()
        if now - self._cache_time < refresh_after and self._tools:
            return dict(self._tools)

        discovered: Dict[str, Dict] = dict(self._tools)  # start with static map
        for server_name, info in list(self._registry.items()):
            try:
                if info.get('type') == 'http':
                    client = JSONRPCClient(info.get('endpoint'))
                    resp = client.call('list_tools', {})
                    tools = resp.get('result', {}).get('tools') if isinstance(resp, dict) else None
                elif info.get('type') == 'stdio':
                    cmd = info.get('cmd')
                    client = StdioJSONRPCClient(cmd)
                    try:
                        client.handshake()
                        resp = client.send('list_tools', {})
                    finally:
                        client.close()
                    tools = resp.get('result', {}).get('tools') if isinstance(resp, dict) else None
                else:
                    tools = None

                if tools:
                    for t in tools:
                        name = t.get('name')
                        if not name:
                            continue
                        discovered[name] = {"server": server_name, "schema": t}
            except Exception as e:
                self.logger.debug("Failed to discover tools from %s: %s", server_name, e)
                continue

        # Update cache and internal mapping
        for k, v in discovered.items():
            if k not in self._tools:
                self._tools[k] = v

        self._cache_time = now
        return dict(self._tools)

    def list_all_tools(self) -> Dict[str, Dict]:
        return dict(self._tools)
