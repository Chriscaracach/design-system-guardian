"""
Google Gemini AI Client
Wraps the google-generativeai SDK to implement BaseAIClient.
"""

import os
from typing import Optional, Dict

from ds_guardian.ai.client import BaseAIClient


class GeminiClient(BaseAIClient):
    """Client for Google Gemini API"""

    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini client.

        Args:
            api_key: Google AI API key. Falls back to GEMINI_API_KEY env var.
            model: Gemini model name (default: gemini-1.5-flash)
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL

    def is_available(self) -> bool:
        """Return True if the SDK is installed and an API key is present"""
        if not self.api_key:
            return False
        try:
            import google.generativeai  # noqa: F401
            return True
        except ImportError:
            return False

    def generate(self, prompt: str, system: Optional[str] = None) -> Dict:
        """
        Send a prompt to Gemini and return a normalised response dict.

        Returns:
            {"response": "<text>", "eval_count": <int>}  on success
            {"error": "<message>"}                        on failure
        """
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)

            generation_config = genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096,
            )

            model_kwargs = {"generation_config": generation_config}
            if system:
                model_kwargs["system_instruction"] = system

            model = genai.GenerativeModel(self.model, **model_kwargs)
            response = model.generate_content(prompt)

            text = response.text if response.text else ""
            tokens = (
                response.usage_metadata.total_token_count
                if response.usage_metadata
                else 0
            )

            return {"response": text, "eval_count": tokens}

        except ImportError:
            return {"error": "google-generativeai package not installed. Run: pip install google-generativeai"}
        except Exception as e:
            return {"error": str(e)}
