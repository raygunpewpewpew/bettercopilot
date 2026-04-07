"""A tiny HTTP-based MCP server that returns simple wiki lookups.

This is a minimal JSON-RPC style HTTP server suitable for integration tests
and examples. It does not require external frameworks.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import socket
import threading


class DeepWikiHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length).decode('utf-8')
        try:
            req = json.loads(raw)
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"invalid json")
            return

        method = req.get('method')
        if method == 'query':
            q = req.get('params', {}).get('q', '')
            result = {"summary": f"DeepWiki simulated summary for '{q}'"}
        elif method == 'list_tools':
            # Provide a richer tool schema for discovery
            result = {
                "tools": [
                    {
                        "name": "deepwiki",
                        "description": "Lookup short wiki-style summaries",
                        "methods": ["query"],
                        "schema": {
                            "query": {"params": {"q": {"type": "string", "description": "Query string", "examples": ["python"]}}}
                        }
                    }
                ]
            }
        else:
            result = {"message": "unknown method"}

        resp = {"jsonrpc": "2.0", "result": result, "id": req.get('id')}
        body = json.dumps(resp).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_deepwiki(port: int = 8765):
    server = HTTPServer(('localhost', port), DeepWikiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"DeepWiki server running on http://localhost:{port}/")
    return server


if __name__ == '__main__':
    run_deepwiki()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('DeepWiki server stopped')
