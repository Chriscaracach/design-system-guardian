"""
Model configuration — persists the user's chosen AI provider and credentials.
Config file: ~/.config/ds_guardian/model.json
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


PROVIDERS = ['ollama', 'anthropic', 'openai', 'gemini']

PROVIDER_DEFAULTS = {
    'ollama':    'qwen2.5-coder:0.5b',
    'anthropic': 'claude-3-5-haiku-latest',
    'openai':    'gpt-4o-mini',
    'gemini':    'gemini-1.5-flash',
}

PROVIDER_ENV_VARS = {
    'anthropic': 'ANTHROPIC_API_KEY',
    'openai':    'OPENAI_API_KEY',
    'gemini':    'GEMINI_API_KEY',
}

PROVIDER_PACKAGES = {
    'anthropic': 'anthropic',
    'openai':    'openai',
    'gemini':    'google-generativeai',
}

CONFIG_PATH = Path.home() / '.config' / 'ds_guardian' / 'model.json'


@dataclass
class ModelConfig:
    """Persisted AI provider configuration"""
    provider: str = 'ollama'
    model: str = 'qwen2.5-coder:0.5b'
    api_key: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def save(self):
        """Write config to ~/.config/ds_guardian/model.json"""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> 'ModelConfig':
        """
        Load config from disk.
        Returns defaults (ollama) if no config file exists yet.
        """
        if not CONFIG_PATH.exists():
            return cls()
        try:
            data = json.loads(CONFIG_PATH.read_text())
            return cls(
                provider=data.get('provider', 'ollama'),
                model=data.get('model', PROVIDER_DEFAULTS.get(data.get('provider', 'ollama'), 'qwen2.5-coder:0.5b')),
                api_key=data.get('api_key'),
            )
        except Exception:
            return cls()

    @classmethod
    def exists(cls) -> bool:
        return CONFIG_PATH.exists()

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def resolved_api_key(self) -> Optional[str]:
        """Return the API key from config, falling back to the env var."""
        if self.api_key:
            return self.api_key
        env_var = PROVIDER_ENV_VARS.get(self.provider)
        if env_var:
            return os.environ.get(env_var)
        return None

    def display(self) -> str:
        """Human-readable one-liner for the current config."""
        key = self.resolved_api_key()
        if key:
            masked = key[:6] + '*' * max(0, len(key) - 6)
            key_display = f'  api_key : {masked}'
        else:
            key_display = '  api_key : (not set)'
        return (
            f'  provider: {self.provider}\n'
            f'  model   : {self.model}\n'
            f'{key_display}'
        )
