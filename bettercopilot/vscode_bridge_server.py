"""A minimal HTTP bridge for VS Code to communicate with the Python orchestrator.

Endpoints:
 - POST /ask {question: str}
 - POST /fix {path: str, content: str}
 - POST /analyze {path: str}

This server is intentionally tiny and suitable for local use or testing.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from urllib.parse import urlparse
from typing import Dict

from bettercopilot.orchestrator.orchestrator import Orchestrator
from bettercopilot.orchestrator.task import Task
from bettercopilot.providers.ollama_local import OllamaLocalProvider
from bettercopilot.mcp.registry import MCPRegistry
import uuid


class BridgeHandler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        b = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length).decode('utf-8')
        try:
            data = json.loads(raw)
        except Exception:
            self._send({'error': 'invalid_json'}, code=400)
            return

        path = urlparse(self.path).path
        providers = {"ollama_local": OllamaLocalProvider()}
        registry = MCPRegistry()
        orch = Orchestrator(providers, registry)

        if path == '/ask':
            q = data.get('question')
            task = Task(id=str(uuid.uuid4()), goal=q, provider='ollama_local')
            res = orch.run_task(task)
            self._send(res)
        elif path == '/fix':
            p = data.get('path')
            content = data.get('content')
            # write a temp file and run fix
            task = Task(id=str(uuid.uuid4()), goal=f"Fix file {p}", provider='ollama_local')
            res = orch.run_task(task)
            self._send(res)
        elif path == '/analyze':
            rom = data.get('path')
            task = Task(id=str(uuid.uuid4()), goal=f"Analyze ROM {rom}", provider='ollama_local', tools=['fusion_inspect'])
            res = orch.run_task(task)
            self._send(res)
        else:
            self._send({'error': 'unknown_endpoint'}, code=404)


def run_server(port: int = 8767):
    server = HTTPServer(('localhost', port), BridgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"VSCode bridge server running on http://localhost:{port}")
    return server


if __name__ == '__main__':
    run_server()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('Bridge stopped')
