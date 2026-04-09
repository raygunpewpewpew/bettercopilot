import threading
import time
from bettercopilot.ui.gui.api import GUIAPI


class MockProvider:
    def __init__(self):
        self.called = False
        self.messages = None

    def generate(self, messages, progress_callback=None):
        # record and assert on messages
        self.called = True
        self.messages = list(messages)
        # return a JSON-text string as many providers do
        return {'text': '{"chat": "ok", "diffs": []}'}


class FakeOrch:
    def __init__(self, provider):
        self.providers = {'mock': provider}


def test_run_ask_chat_only_inserts_empty_diff_instruction():
    prov = MockProvider()
    gui = GUIAPI()
    # override orchestrator with fake one containing our mock provider
    gui.orchestrator = FakeOrch(prov)
    gui.direct_chat = True
    gui.force_json_output = True

    # Run ask with /chat prefix and request the mock provider
    worker = gui.run_ask('/chat Hello please', provider_override='mock')

    # Wait for worker to finish (headless Worker exposes join)
    try:
        if hasattr(worker, 'join'):
            worker.join(timeout=5)
        else:
            # fallback: give a short sleep
            time.sleep(0.5)
    except Exception:
        time.sleep(0.2)

    assert prov.called is True
    # Ensure at least one system message asks for empty diffs
    sys_msgs = [m for m in (prov.messages or []) if m.get('role') == 'system']
    assert any(('diff' in (m.get('content') or '').lower() and 'empty' in (m.get('content') or '').lower()) for m in sys_msgs)
