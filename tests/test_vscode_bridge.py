import requests
import threading
import time
from bettercopilot.vscode_bridge_server import run_server


def test_vscode_bridge_ask():
    server = run_server(port=8770)
    time.sleep(0.1)
    try:
        resp = requests.post('http://localhost:8770/ask', json={'question': 'Say hello'})
        assert resp.status_code == 200
        data = resp.json()
        assert 'task_id' in data
    finally:
        server.shutdown()
