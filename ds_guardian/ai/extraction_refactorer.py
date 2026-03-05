"""
Extraction Refactorer Module
Uses AI to extract design tokens from raw CSS content
"""

import re
import json
from typing import Dict, List

from ds_guardian.ai.client import OllamaClient
from ds_guardian.core.extractor import DesignToken, ExtractedDesignSystem, DesignSystemExtractor


SYSTEM_PROMPT = """You are a design system expert. Your job is to analyze CSS code and extract reusable design tokens.

Rules:
1. Identify hardcoded values that should become CSS variables: colors, font sizes, font weights, spacing values, border radii, border widths, box shadows, transitions, and animations.
2. Group tokens by category: colors, typography, spacing, borders, shadows, motion.
3. Pick a clear, semantic CSS variable name for each unique value (e.g. --color-primary, --font-size-sm, --space-4).
4. If the same value appears multiple times, define it only once with the best name.
5. Do NOT include values that are already CSS variables (var(--...)).
6. Do NOT include values like 0, none, auto, inherit, initial, or other CSS keywords.
7. Return ONLY valid JSON — no markdown, no explanations, no code fences.

Output format (strict JSON):
{
  "colors": [
    {"name": "--color-primary", "value": "#2563eb"},
    {"name": "--color-gray-900", "value": "#111827"}
  ],
  "typography": [
    {"name": "--font-size-sm", "value": "0.875rem"},
    {"name": "--font-weight-bold", "value": "700"}
  ],
  "spacing": [
    {"name": "--space-4", "value": "16px"}
  ],
  "borders": [
    {"name": "--radius-md", "value": "6px"}
  ],
  "shadows": [
    {"name": "--shadow-md", "value": "0 4px 6px rgba(0,0,0,0.1)"}
  ],
  "motion": [
    {"name": "--transition-base", "value": "all 0.2s ease"}
  ]
}

Only include categories that have tokens. Use empty arrays for categories with no tokens (they will be omitted).
"""


class ExtractionResult:
    """Result from AI extraction"""

    def __init__(self, success: bool, extracted: ExtractedDesignSystem = None, error: str = None, tokens_used: int = 0):
        self.success = success
        self.extracted = extracted
        self.error = error
        self.tokens_used = tokens_used


class CSSExtractionRefactorer:
    """Extracts design tokens from CSS using AI"""

    def __init__(self, client: OllamaClient):
        self.client = client
        self._ds_extractor = DesignSystemExtractor()

    def extract(self, combined_css: str) -> ExtractionResult:
        """
        Extract design tokens from combined CSS content.

        Args:
            combined_css: All CSS content concatenated

        Returns:
            ExtractionResult with an ExtractedDesignSystem
        """
        if not combined_css.strip():
            return ExtractionResult(success=False, error="Empty CSS content")

        existing_vars = self._ds_extractor.collect_existing_vars(combined_css)

        prompt = self._build_prompt(combined_css)
        response = self.client.generate(prompt, system=SYSTEM_PROMPT)

        if "error" in response:
            return ExtractionResult(success=False, error=response["error"])

        raw = response.get("response", "").strip()
        if not raw:
            return ExtractionResult(success=False, error="Empty response from AI")

        tokens_used = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)

        try:
            data = self._parse_json_response(raw)
        except Exception as e:
            return ExtractionResult(success=False, error=f"Could not parse AI response: {e}\n\nRaw response:\n{raw[:500]}")

        tokens_by_category: Dict[str, List[DesignToken]] = {}
        for category, entries in data.items():
            if not isinstance(entries, list) or not entries:
                continue
            token_list = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name", "").strip()
                value = entry.get("value", "").strip()
                if name and value:
                    token_list.append(DesignToken(name=name, value=value, category=category))
            if token_list:
                tokens_by_category[category] = token_list

        extracted = ExtractedDesignSystem(
            tokens_by_category=tokens_by_category,
            existing_vars=existing_vars,
        )

        return ExtractionResult(success=True, extracted=extracted, tokens_used=tokens_used)

    def _build_prompt(self, css_content: str) -> str:
        max_chars = 12000
        truncated = css_content[:max_chars]
        if len(css_content) > max_chars:
            truncated += "\n/* ... (truncated for brevity) */"
        return f"""Analyze the following CSS and extract all reusable design tokens.\n\nCSS:\n{truncated}\n\nReturn ONLY the JSON object as described."""

    def _parse_json_response(self, raw: str) -> dict:
        """Parse JSON from the AI response, stripping any markdown fences."""
        cleaned = re.sub(r'```(?:json)?\s*', '', raw).replace('```', '').strip()
        return json.loads(cleaned)
