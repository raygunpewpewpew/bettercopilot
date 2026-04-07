"""Provider configuration loader.

Loads `providers.toml` if present and allows overriding via environment
variables. Designed to be lightweight and safe for tests.
"""
import os
import tomllib
from pathlib import Path
from typing import Dict, Any


def load_config(path: str = None) -> Dict[str, Any]:
    cfg_path = Path(path) if path else Path(__file__).resolve().parent / 'providers.toml'
    config: Dict[str, Any] = {}
    if cfg_path.exists():
        try:
            with open(cfg_path, 'rb') as f:
                config = tomllib.load(f)
        except Exception:
            config = {}

    # Overlay env vars (e.g., BETTERCOPILOT_GROQ_API_KEY)
    for provider in list(config.keys()):
        provider_upper = provider.upper()
        api_key = os.environ.get(f'BETTERCOPILOT_{provider_upper}_API_KEY')
        if api_key:
            config.setdefault(provider, {})['api_key'] = api_key
    return config


def get_provider_config(name: str, path: str = None) -> Dict[str, Any]:
    cfg = load_config(path)
    return cfg.get(name, {})
