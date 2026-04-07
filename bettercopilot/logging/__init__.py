"""Lightweight JSONL run logging for BetterCopilot.

Provides functions to write structured events per run into `logs/` as JSONL.
This module is intentionally small and does not replace the stdlib `logging`.
"""
from .events import init_run, log_event, write_summary, enable_trace

__all__ = ["init_run", "log_event", "write_summary", "enable_trace"]
