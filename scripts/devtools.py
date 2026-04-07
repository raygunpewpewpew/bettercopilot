"""Developer utilities for debugging providers and MCP clients."""
from bettercopilot.providers.groq_free import GroqFreeProvider
from bettercopilot.mcp.client import JSONRPCClient


def debug_provider():
    p = GroqFreeProvider()
    out = p.generate([{"role": "user", "content": "Echo this"}])
    print(out)


def ping_deepwiki():
    client = JSONRPCClient('http://localhost:8765/')
    print(client.call('query', {'q': 'test'}))


if __name__ == '__main__':
    debug_provider()
