"""`ai rom` command implementation for ROM-related actions."""
from bettercopilot.mcp.registry import MCPRegistry
from bettercopilot.orchestrator.tool_router import ToolRouter
import pprint


def run(action: str, rom_path: str):
    registry = MCPRegistry()
    router = ToolRouter(registry)
    if action == 'analyze':
        tc = {"tool": "fusion_inspect", "method": "inspect", "params": {"name": rom_path}}
        resp = router.route_call(tc)
        print('Analysis result:')
        pprint.pprint(resp)
    else:
        print('Unknown action:', action)
