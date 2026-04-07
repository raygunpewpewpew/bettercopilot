from bettercopilot.config import get_provider_config


def test_provider_config_loads():
    cfg = get_provider_config('groq')
    assert isinstance(cfg, dict)
