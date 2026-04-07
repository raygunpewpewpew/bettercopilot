import threading
import time
from bettercopilot.mcp.client import JSONRPCClient
from bettercopilot.mcp.servers.deepwiki_server import run_deepwiki


def test_deepwiki_http():
    server = run_deepwiki(port=8766)
    time.sleep(0.1)
    client = JSONRPCClient('http://localhost:8766/')
    resp = client.call('query', {'q': 'python'})
    assert 'result' in resp
    server.shutdown()
