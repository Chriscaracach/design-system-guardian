"""
OpenAI AI Client
Wraps the OpenAI SDK to implement BaseAIClient.
"""

import os
from typing import Optional, Dict

from ds_guardian.ai.client import BaseAIClient


class OpenAIClient(BaseAIClient):
    """Client for OpenAI API"""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            model: OpenAI model name (default: gpt-4o-mini)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL

    def is_available(self) -> bool:
        """Return True if the SDK is installed and an API key is present"""
        if not self.api_key:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def generate(self, prompt: str, system: Optional[str] = None) -> Dict:
        """
        Send a prompt to OpenAI and return a normalised response dict.

        Returns:
            {"response": "<text>", "eval_count": <int>}  on success
            {"error": "<message>"}                        on failure
        """
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096,
                temperature=0.3,
            )

            text = response.choices[0].message.content or "" if response.choices else ""
            tokens = response.usage.total_tokens if response.usage else 0

            return {"response": text, "eval_count": tokens}

        except ImportError:
            return {"error": "openai package not installed. Run: pip install openai"}
        except Exception as e:
            return {"error": str(e)}
