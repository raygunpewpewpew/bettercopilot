"""Event logging helpers that write JSONL files for each run.

Usage:
    run_id = init_run(metadata={...})
    log_event(run_id, {"provider_call": {...}})
    write_summary(run_id, {"final": ...})
"""
import json
from pathlib import Path
from typing import Dict, Any
import time
import threading

_lock = threading.Lock()
_trace_enabled = False


def enable_trace(enabled: bool = True):
    global _trace_enabled
    _trace_enabled = bool(enabled)


def _logs_dir() -> Path:
    base = Path(__file__).resolve().parents[2]
    logs = base / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def init_run(metadata: Dict[str, Any] = None) -> str:
    run_id = str(int(time.time() * 1000))
    entry = {"run_id": run_id, "event": "init", "ts": time.time(), "metadata": metadata or {}}
    p = _logs_dir() / f"{run_id}.jsonl"
    with _lock, p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")
    return run_id


def log_event(run_id: str, event: Dict[str, Any]):
    if not _trace_enabled and event.get('level') == 'debug':
        return
    p = _logs_dir() / f"{run_id}.jsonl"
    entry = {"run_id": run_id, "event": event, "ts": time.time()}
    with _lock, p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")


def write_summary(run_id: str, summary: Dict[str, Any]):
    p = _logs_dir() / f"{run_id}.jsonl"
    entry = {"run_id": run_id, "event": {"summary": summary}, "ts": time.time()}
    with _lock, p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")
