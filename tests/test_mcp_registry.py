from bettercopilot.mcp.registry import MCPRegistry


def test_registry_tool_mapping():
    reg = MCPRegistry()
    # default tools include deepwiki and fusion_inspect
    tools = reg.list_tools()
    assert isinstance(tools, list)
    # Register a new fake server and tool
    reg.register_server('myserver', {'type': 'http', 'endpoint': 'http://localhost:9999/'})
    reg.register_tool('mytool', 'myserver', schema={'methods': ['do']})
    assert reg.get_server_for_tool('mytool') is not None
    assert 'mytool' in reg.list_tools()
