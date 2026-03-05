"""
Anthropic Claude AI Client
Wraps the Anthropic SDK to implement BaseAIClient.
"""

import os
from typing import Optional, Dict

from ds_guardian.ai.client import BaseAIClient


class AnthropicClient(BaseAIClient):
    """Client for Anthropic Claude API"""

    DEFAULT_MODEL = "claude-3-5-haiku-latest"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Claude model name (default: claude-3-5-haiku-latest)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL

    def is_available(self) -> bool:
        """Return True if the SDK is installed and an API key is present"""
        if not self.api_key:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def generate(self, prompt: str, system: Optional[str] = None) -> Dict:
        """
        Send a prompt to Claude and return a normalised response dict.

        Returns:
            {"response": "<text>", "eval_count": <int>}  on success
            {"error": "<message>"}                        on failure
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system

            message = client.messages.create(**kwargs)

            text = message.content[0].text if message.content else ""
            tokens = (
                (message.usage.input_tokens or 0) + (message.usage.output_tokens or 0)
                if message.usage
                else 0
            )

            return {"response": text, "eval_count": tokens}

        except ImportError:
            return {"error": "anthropic package not installed. Run: pip install anthropic"}
        except Exception as e:
            return {"error": str(e)}
