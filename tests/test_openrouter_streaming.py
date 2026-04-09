import json

from bettercopilot.providers.openrouter import OpenRouterProvider


class DummyResp:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        return None

    def iter_lines(self, decode_unicode=True):
        for l in self._lines:
            yield l

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummySession:
    def __init__(self, lines):
        self.lines = lines

    def post(self, *args, **kwargs):
        return DummyResp(self.lines)


def test_stream_single_json_line():
    provider = OpenRouterProvider(api_key='fake', model='gpt-4o-mini', base_url='http://example')
    lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        '',
        'data: [DONE]',
        '',
    ]
    provider.session = DummySession(lines)
    partials = []

    def progress(event, d):
        if event == 'provider_stream' and isinstance(d, dict):
            partials.append(d.get('partial'))

    out = provider.generate([{'role': 'user', 'content': 'hi'}], stream=True, progress_callback=progress)
    assert isinstance(out, dict)
    assert out.get('text') == 'Hello'
    assert any('Hello' in (p or '') for p in partials)


def test_stream_multiple_json_lines():
    provider = OpenRouterProvider(api_key='fake', model='gpt-4o-mini', base_url='http://example')
    lines = [
        'data: {"a":"one"}',
        'data: {"b":"two"}',
        '',
        'data: [DONE]',
        '',
    ]
    provider.session = DummySession(lines)
    partials = []

    def progress(event, d):
        if event == 'provider_stream' and isinstance(d, dict):
            partials.append(d.get('partial'))

    out = provider.generate([{'role': 'user', 'content': 'hi'}], stream=True, progress_callback=progress)
    # both values should be concatenated into final text
    assert out.get('text') == 'onetwo'
    assert any('one' in (p or '') for p in partials)
    assert any('two' in (p or '') for p in partials)


def test_stream_detects_patch_in_events():
    provider = OpenRouterProvider(api_key='fake', model='gpt-4o-mini', base_url='http://example')
    patch_text = '--- a/file\n+++ b/file\n@@ -1 +1 @@\n-foo\n+bar\n'
    lines = [
        f'data: {{"patch": "{patch_text}"}}',
        '',
        'data: [DONE]',
        '',
    ]
    provider.session = DummySession(lines)
    out = provider.generate([{'role': 'user', 'content': 'make edit'}], stream=True)
    assert 'diffs' in out and out['diffs'], 'Expected diffs to be detected in streaming events'
    assert any('--- a/file' in d for d in out['diffs'])
