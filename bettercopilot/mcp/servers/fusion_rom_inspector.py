"""A stdio-based MCP server that performs a handshake and lazy-loads heavy modules.

This example reads line-delimited JSON requests from stdin and writes line
delimited JSON responses to stdout. It responds to a `handshake` method
immediately and defers heavy imports until after the handshake.
"""
import sys
import json
import time
import threading


def _lazy_load_heavy():
    # Simulate a heavy import or initialization that should be deferred
    time.sleep(0.2)


def handle_line(line: str, state: dict):
    try:
        req = json.loads(line)
    except Exception:
        return json.dumps({"error": "invalid_json"})

    method = req.get('method')
    if method == 'handshake':
        # Instant-handshake: reply immediately
        # Start background lazy load
        if not state.get('loaded'):
            threading.Thread(target=_lazy_load_heavy, daemon=True).start()
            state['loaded'] = True
        return json.dumps({"jsonrpc": "2.0", "result": {"handshake": "ok"}, "id": req.get('id')})
    if method == 'list_tools':
        # Return tool schema for discovery
        tools = [
            {
                "name": "fusion_inspect",
                "description": "Inspect ROM files for metadata and basic analysis",
                "methods": ["inspect"],
                "schema": {
                    "inspect": {"params": {"name": {"type": "string", "description": "ROM path or identifier", "examples": ["game.gba"]}}}
                }
            }
        ]
        return json.dumps({"jsonrpc": "2.0", "result": {"tools": tools}, "id": req.get('id')})
    elif method == 'inspect':
        # A tiny inspector that pretends to analyze a ROM
        params = req.get('params', {})
        name = params.get('name', '<unknown>')
        return json.dumps({"jsonrpc": "2.0", "result": {"analysis": f"Simulated ROM analysis for {name}"}, "id": req.get('id')})
    else:
        return json.dumps({"jsonrpc": "2.0", "error": {"message": "unknown method"}, "id": req.get('id')})


def main():
    state = {"loaded": False}
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        resp = handle_line(line, state)
        sys.stdout.write(resp + "\n")
        sys.stdout.flush()


if __name__ == '__main__':
    main()
