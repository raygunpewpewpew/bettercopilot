"""Global debug logger for the application.

Writes JSONL debug lines to a single `debug_log.txt` (rotated) and
notifies registered GUI callbacks so the UI can show the consolidated
log in real time.

Provides lightweight function-call tracing for in-package calls (optional).
"""
from pathlib import Path
import json
import time
import threading
import sys
import traceback
from typing import Callable, Optional

_lock = threading.Lock()
_callbacks = []  # type: list[Callable[[dict], None]]
_recent_events = []  # recent events buffer for new UI subscribers
_recent_max = 1000

# default logfile location (project root / DebugLogs/debug_log.txt)
# keep debug files out of repo root in a dedicated folder
_try_base = Path(__file__).resolve().parents[2]
_default_log = Path.cwd() / 'DebugLogs' / 'debug_log.txt'
try:
    # prefer project root when available
    _default_log = _try_base / 'DebugLogs' / 'debug_log.txt'
except Exception:
    pass

_max_bytes = 5 * 1024 * 1024


def _rotate_if_needed(p: Path, new_bytes: int = 0):
    try:
        if p.exists() and p.stat().st_size + new_bytes > _max_bytes:
            rotated = p.with_name(f"{p.stem}_{time.strftime('%Y%m%d_%H%M%S')}.txt")
            try:
                p.replace(rotated)
            except Exception:
                try:
                    p.rename(rotated)
                except Exception:
                    pass
    except Exception:
        pass


def write(event: dict, logfile: Optional[Path] = None) -> bool:
    """Write a JSONL debug `event` to the global logfile and notify callbacks.

    `event` should be JSON-serializable. Returns True when a write succeeded.
    """
    if not isinstance(event, dict):
        try:
            event = {'ts': time.time(), 'event': 'debug', 'text': str(event)}
        except Exception:
            event = {'ts': time.time(), 'event': 'debug', 'text': '<unserializable>'}

    if 'ts' not in event:
        event['ts'] = time.time()

    s = None
    try:
        s = json.dumps(event, ensure_ascii=False)
    except Exception:
        try:
            event['text'] = str(event.get('text', ''))
            s = json.dumps(event, ensure_ascii=False)
        except Exception:
            s = str(event)

    target = logfile or _default_log

    written = False
    with _lock:
        try:
            b = len(s.encode('utf-8')) + 1
            _rotate_if_needed(target, new_bytes=b)
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, 'a', encoding='utf-8') as f:
                f.write(s + '\n')
            written = True
            # record recent events for any UI that registers later
            try:
                if isinstance(event, dict):
                    _recent_events.append(event.copy())
                else:
                    _recent_events.append({'ts': time.time(), 'event': 'debug', 'text': str(event)})
                if len(_recent_events) > _recent_max:
                    del _recent_events[0:len(_recent_events) - _recent_max]
            except Exception:
                pass
        except Exception:
            written = False

    # notify callbacks (best-effort, do not raise)
    try:
        for cb in list(_callbacks):
            try:
                cb(event)
            except Exception:
                pass
    except Exception:
        pass

    return written


def register_callback(cb: Callable[[dict], None]):
    """Register a callback to be invoked for each debug event (in-process).

    Callback receives the parsed event dict.
    """
    try:
        if cb and callable(cb):
            _callbacks.append(cb)
            # replay recent events to the new subscriber (best-effort)
            try:
                for ev in list(_recent_events):
                    try:
                        cb(ev)
                    except Exception:
                        pass
            except Exception:
                pass
            return True
    except Exception:
        pass
    return False


def clear_callbacks():
    try:
        _callbacks.clear()
    except Exception:
        pass


# Tracing support -----------------------------------------------------------
_trace_installed = False


def _trace_func(frame, event, arg):
    # Only log 'call' events to reduce volume; restrict to package modules
    try:
        if event != 'call':
            return
        co = frame.f_code
        module = frame.f_globals.get('__name__', '')
        if not module or not module.startswith('bettercopilot'):
            return
        fname = co.co_name
        event_obj = {
            'ts': time.time(),
            'event': 'call',
            'module': module,
            'function': fname,
            'filename': co.co_filename,
            'lineno': co.co_firstlineno,
        }
        # best-effort: write without blocking callback notifications
        write(event_obj)
    except Exception:
        # swallow tracing exceptions to avoid interfering with program
        try:
            write({'ts': time.time(), 'event': 'trace_error', 'error': traceback.format_exc()})
        except Exception:
            pass


def start_tracing(enable: bool = True):
    """Enable function-call tracing for in-package calls.

    This installs a `sys.setprofile` hook and registers it for new threads.
    Tracing generates a large amount of output; use judiciously.
    """
    global _trace_installed
    try:
        if not enable:
            sys.setprofile(None)
            try:
                import threading as _thr
                _thr.setprofile(None)
            except Exception:
                pass
            _trace_installed = False
            return True

        sys.setprofile(_trace_func)
        try:
            import threading as _thr
            _thr.setprofile(_trace_func)
        except Exception:
            pass
        _trace_installed = True
        write({'ts': time.time(), 'event': 'trace_started'})
        return True
    except Exception:
        try:
            write({'ts': time.time(), 'event': 'trace_failed', 'error': traceback.format_exc()})
        except Exception:
            pass
        return False


def log_exception(exc_type, exc_value, exc_tb):
    try:
        tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        write({'ts': time.time(), 'event': 'uncaught_exception', 'type': str(exc_type), 'value': str(exc_value), 'trace': tb})
    except Exception:
        pass


def install_exception_hook():
    try:
        sys.excepthook = log_exception
        # Threading hook for Python 3.8+
        try:
            import threading as _thr
            if hasattr(_thr, 'excepthook'):
                def _on_thread_ex(args):
                    try:
                        import traceback
                        tr = None
                        try:
                            tr = ''.join(traceback.format_exception(getattr(args, 'exc_type', None), getattr(args, 'exc_value', None), getattr(args, 'exc_traceback', None)))
                        except Exception:
                            tr = None
                        try:
                            write({'ts': time.time(), 'event': 'thread_exception', 'thread': getattr(args, 'thread', None), 'exc_type': str(getattr(args, 'exc_type', None)), 'exc_value': str(getattr(args, 'exc_value', None)), 'trace': tr})
                        except Exception:
                            pass
                    except Exception:
                        pass
                try:
                    _thr.excepthook = _on_thread_ex
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        pass
