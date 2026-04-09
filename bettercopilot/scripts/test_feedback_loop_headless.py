from bettercopilot.ui.gui.api import GUIAPI
from bettercopilot.ui.gui import ai_panel


class MockProvider:
    def __init__(self, name, reply_prefix='R'):
        self.name = name
        self.reply_prefix = reply_prefix
        self.called = 0

    def generate(self, messages, progress_callback=None):
        self.called += 1
        # Compose a JSON payload as a string
        chat = f"{self.reply_prefix} reply {self.called}"
        diff = f"--- a\n+++ b\n@@\n+{self.reply_prefix} change {self.called}\n"
        # simulate streaming preview
        try:
            if callable(progress_callback):
                progress_callback('provider_stream', {'provider': self.name, 'partial': chat})
        except Exception:
            pass
        return { 'text': f'{{"chat": "{chat}", "diffs": ["{diff}"]}}', 'raw': {'provider': self.name}}


class SimpleEditor:
    def __init__(self, text='initial'):
        self._text = text

    def get_text(self):
        return self._text

    def apply_diff(self, diff_text=None, final_text=None):
        if final_text is not None:
            self._text = final_text
        elif diff_text is not None:
            # naive: append a marker for applied diff
            self._text += '\n' + str(diff_text)

    def set_text(self, t):
        self._text = t

    def save_file(self, *args, **kwargs):
        return True


class DiffViewer:
    def __init__(self):
        self._diff = None

    def set_diff(self, d):
        self._diff = d

    def get_diff(self):
        return self._diff


def run_headless_feedback():
    gui = GUIAPI()
    # headless panels
    panel1 = ai_panel.AIPanel()
    panel2 = ai_panel.AIPanel()
    panel1.set_provider_label('p1')
    panel2.set_provider_label('p2')
    gui.ai_panel = panel1
    gui.ai_panel_ollama = panel2
    gui.diff_viewer = DiffViewer()
    gui.editor = SimpleEditor('start')

    # inject fake orchestrator providers
    class FakeOrch:
        def __init__(self):
            self.providers = {'p1': MockProvider('p1','A'), 'p2': MockProvider('p2','B')}

    gui.orchestrator = FakeOrch()

    # run feedback starting with p1, ask for 2 iterations
    w = gui.run_ask('/feedback=2 Improve this', provider_override='p1')
    # If worker has join, wait
    try:
        if hasattr(w, 'join'):
            w.join(timeout=5)
    except Exception:
        pass

    print('Editor text after feedback:\n', gui.editor.get_text())
    print('Diff viewer diff:\n', gui.diff_viewer.get_diff())
    print('Panel1 history:', panel1.get_history())
    print('Panel2 history:', panel2.get_history())


if __name__ == '__main__':
    run_headless_feedback()
