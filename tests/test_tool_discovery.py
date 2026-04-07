import time
from bettercopilot.mcp.servers.deepwiki_server import run_deepwiki
from bettercopilot.mcp.registry import MCPRegistry


def test_discover_tools():
    server = run_deepwiki(port=8765)
    time.sleep(0.05)
    reg = MCPRegistry()
    discovered = reg.discover_tools()
    # Ensure deepwiki is discoverable
    assert 'deepwiki' in discovered
    # fusion_inspect should appear via stdio discovery mapping
    assert 'fusion_inspect' in reg.list_tools()
    server.shutdown()
