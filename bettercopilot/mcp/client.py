"""JSON-RPC clients for HTTP and stdio MCP servers.

This module provides a minimal JSON-RPC client that supports HTTP and
stdio-based MCP servers. The implementations are intentionally lightweight
and suitable for local development and testing.
"""
from typing import Any, Dict, Optional
import json
import requests
import subprocess
import threading
import queue
import logging
import time


class JSONRPCClient:
    """Simple JSON-RPC over HTTP client."""

    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url
        self.timeout = timeout
        self.logger = logging.getLogger("JSONRPCClient")

    def call(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}
        self.logger.debug("HTTP JSON-RPC call %s -> %s", self.base_url, payload)
        resp = requests.post(self.base_url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


class StdioJSONRPCClient:
    """JSON-RPC over stdio (spawned subprocess).

    The protocol is line-delimited JSON messages. This client writes JSON
    request lines to the child's stdin and reads response lines from stdout.
    A simple handshake method is provided.
    """

    def __init__(self, cmd: list, read_timeout: float = 5.0):
        self.cmd = cmd
        self.read_timeout = read_timeout
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self._out_queue = queue.Queue()
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()
        self.logger = logging.getLogger("StdioJSONRPCClient")

    def _read_stdout(self):
        for line in self.proc.stdout:
            self._out_queue.put(line.rstrip("\n"))

    def send(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        req = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": int(time.time() * 1000) % 100000}
        line = json.dumps(req)
        self.logger.debug("Stdio send: %s", line)
        try:
            self.proc.stdin.write(line + "\n")
            self.proc.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError("Child process stdin closed")

        try:
            resp_line = self._out_queue.get(timeout=self.read_timeout)
        except queue.Empty:
            raise TimeoutError("Timed out waiting for stdio response")
        try:
            return json.loads(resp_line)
        except Exception:
            self.logger.exception("Failed to parse response: %s", resp_line)
            return {"error": "invalid_response", "raw": resp_line}

    def handshake(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Perform an instant-handshake pattern with the stdio server."""
        return self.send("handshake", {})

    def close(self):
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
        except Exception:
            pass
