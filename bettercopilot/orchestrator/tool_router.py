"""Tool routing logic for the orchestrator.

This router resolves a tool call to the appropriate MCP server based on the
`MCPRegistry` mapping and forwards the call over HTTP or stdio JSON-RPC.
"""
from typing import Dict, Any, Optional
from ..mcp.client import JSONRPCClient, StdioJSONRPCClient


class ToolRouter:
    def __init__(self, registry):
        self.registry = registry

    def route_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Route and execute a tool_call.

        tool_call expected shape: {"tool": "name", "method": "method", "params": {...}}
        Returns a structured dict with server info and response.
        """
        # Normalize
        tool_name = tool_call.get('tool') or tool_call.get('name')
        method = tool_call.get('method') or tool_call.get('action') or 'call'
        params = tool_call.get('params') or tool_call.get('args') or {}

        server_info = self.registry.get_server_for_tool(tool_name)
        if not server_info:
            return {"tool": tool_name, "error": "no_server_found"}

        try:
            if server_info.get('type') == 'http':
                client = JSONRPCClient(server_info.get('endpoint'))
                resp = client.call(method, params)
                # normalize response text
                resp_text = resp.get('result') if isinstance(resp, dict) else resp
                return {"tool": tool_name, "server": server_info, "response": resp, "response_text": str(resp_text)}
            elif server_info.get('type') == 'stdio':
                cmd = server_info.get('cmd')
                client = StdioJSONRPCClient(cmd)
                try:
                    hk = client.handshake()
                    resp = client.send(method, params)
                finally:
                    client.close()
                resp_text = resp.get('result') if isinstance(resp, dict) else resp
                return {"tool": tool_name, "server": server_info, "response": resp, "response_text": str(resp_text)}
            else:
                return {"tool": tool_name, "error": "unsupported_server_type", "server": server_info}
        except Exception as e:
            return {"tool": tool_name, "error": str(e), "server": server_info}

