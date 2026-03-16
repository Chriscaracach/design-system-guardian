"""
Extraction Refactorer Module
Uses AI to extract design tokens from a pre-processed structured value map.
The value map is built by CSSValueAnalyzer and contains frequency + context data
for each unique CSS value — no raw CSS blobs, no truncation.
"""

import re
import json
from typing import Dict, List

from ds_guardian.ai.client import BaseAIClient
from ds_guardian.core.extractor import DesignToken, ExtractedDesignSystem, DesignSystemExtractor
from ds_guardian.core.value_analyzer import ValueMap


SYSTEM_PROMPT = """You are a design system expert. Your job is to analyse a pre-processed summary of CSS values found in a codebase and assign each value a semantic design token name.

You are given a structured list where each line describes one unique CSS value:
  value="..." frequency=N properties=[prop1 (Nx), prop2 (Nx)] selectors=[sel1, sel2]

- frequency: how many times this value appears across all CSS files
- properties: which CSS properties use it and how often
- selectors: example CSS selectors where it appears

Rules:
1. Use frequency and property/selector context to choose a semantic token name.
   Example: value="#2563eb" used 14x as background-color in .btn-primary → --color-action-primary
   Example: value="4px" used 8x as border-radius, 3x in .card → --radius-sm
2. Group tokens by category: colors, typography, spacing, borders, shadows, motion.
3. Each value gets exactly one token — do not create duplicates.
4. Prefer scale-based names for spacing/typography (--space-4, --font-size-sm) and semantic names for colors (--color-primary, not --color-2563eb).
5. Do NOT invent values — use the exact value as given.
6. Return ONLY valid JSON — no markdown, no explanations, no code fences.

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

Only include categories that have tokens.
"""


class ExtractionResult:
    """Result from AI extraction"""

    def __init__(self, success: bool, extracted: ExtractedDesignSystem = None, error: str = None, tokens_used: int = 0):
        self.success = success
        self.extracted = extracted
        self.error = error
        self.tokens_used = tokens_used


class CSSExtractionRefactorer:
    """Extracts design tokens from a structured ValueMap using AI."""

    def __init__(self, client: BaseAIClient):
        self.client = client
        self._ds_extractor = DesignSystemExtractor()

    def extract(self, value_map: ValueMap, existing_css: str = "") -> ExtractionResult:
        """
        Extract design tokens from a pre-processed ValueMap.

        Args:
            value_map: Structured value map from CSSValueAnalyzer
            existing_css: Raw CSS (used only to collect existing var() declarations)

        Returns:
            ExtractionResult with an ExtractedDesignSystem
        """
        if not value_map.usages:
            return ExtractionResult(success=False, error="No trackable CSS values found")

        existing_vars = self._ds_extractor.collect_existing_vars(existing_css) if existing_css else []

        prompt = self._build_prompt(value_map)
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

    def _build_prompt(self, value_map: ValueMap) -> str:
        summary = value_map.format_for_prompt(max_values=200)
        return (
            "Analyse the following CSS value summary and assign each value a semantic design token name.\n\n"
            "CSS Value Summary:\n"
            f"{summary}\n\n"
            "Return ONLY the JSON object as described."
        )

    def _parse_json_response(self, raw: str) -> dict:
        """Parse JSON from the AI response, stripping any markdown fences."""
        cleaned = re.sub(r'```(?:json)?\s*', '', raw).replace('```', '').strip()
        return json.loads(cleaned)
