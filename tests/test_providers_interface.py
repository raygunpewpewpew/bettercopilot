from bettercopilot.providers.groq_free import GroqFreeProvider
from bettercopilot.providers.gemini_free import GeminiFreeProvider
from bettercopilot.providers.perplexity_free import PerplexityFreeProvider
from bettercopilot.providers.huggingchat import HuggingChatProvider
from bettercopilot.providers.ollama_local import OllamaLocalProvider


def test_providers_interface_fields():
    providers = [GroqFreeProvider(), GeminiFreeProvider(), PerplexityFreeProvider(), HuggingChatProvider(), OllamaLocalProvider()]
    msgs = [{"role": "user", "content": "Hello"}]
    for p in providers:
        out = p.generate(msgs)
        assert isinstance(out, dict)
        assert 'text' in out
        assert 'tool_calls' in out
        assert 'raw' in out
