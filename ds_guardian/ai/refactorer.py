"""
CSS Refactorer Module
Resolves ambiguous CSS declarations using AI.
Deterministic substitutions are handled by core/substitutor.py.
AI is only called when the same value maps to multiple token candidates.
"""

import re
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

from ds_guardian.ai.client import BaseAIClient
from ds_guardian.core.substitutor import AmbiguousDeclaration


@dataclass
class AmbiguityResult:
    """Result from AI ambiguity resolution"""
    success: bool
    decisions: Dict[int, str]  # index → chosen token name
    tokens_used: int = 0
    error: Optional[str] = None


class CSSRefactorer:
    """
    Resolves ambiguous CSS declarations using AI.

    Ambiguous = the same CSS value matches 2 or more token candidates.
    AI receives only those declarations (with selector + property context)
    and picks the most semantically appropriate token for each.
    """

    SYSTEM_PROMPT = """You are a CSS design system expert. You are given a list of CSS declarations where the value matches multiple design token candidates. For each declaration, choose the most semantically appropriate token based on the CSS property and selector context.

Rules:
1. Consider the CSS property name — e.g. a 4px value on border-radius suggests --radius-*, not --space-*
2. Consider the selector name — .btn-primary suggests a primary-action token
3. Only pick from the provided candidates — do not invent new token names
4. If truly ambiguous, prefer the more specific token name
5. Return ONLY valid JSON — no markdown, no explanations

Output format (strict JSON array, one entry per input declaration, in the same order):
[
  {"index": 0, "token": "--radius-sm"},
  {"index": 1, "token": "--color-border"}
]"""

    def __init__(self, client: BaseAIClient):
        self.client = client

    def resolve_ambiguous(
        self,
        ambiguous: List[AmbiguousDeclaration],
    ) -> AmbiguityResult:
        """
        Ask AI to resolve a list of ambiguous declarations.

        Args:
            ambiguous: List of AmbiguousDeclaration from CSSSubstitutor

        Returns:
            AmbiguityResult with a decisions dict mapping index → token name
        """
        if not ambiguous:
            return AmbiguityResult(success=True, decisions={})

        prompt = self._build_prompt(ambiguous)
        response = self.client.generate(prompt, system=self.SYSTEM_PROMPT)

        if "error" in response:
            return AmbiguityResult(
                success=False,
                decisions={},
                error=response["error"]
            )

        raw = response.get("response", "").strip()
        if not raw:
            return AmbiguityResult(
                success=False,
                decisions={},
                error="Empty response from AI"
            )

        tokens_used = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)

        try:
            decisions = self._parse_response(raw, ambiguous)
        except Exception as e:
            return AmbiguityResult(
                success=False,
                decisions={},
                error=f"Could not parse AI response: {e}\n\nRaw:\n{raw[:400]}"
            )

        return AmbiguityResult(success=True, decisions=decisions, tokens_used=tokens_used)

    def _build_prompt(self, ambiguous: List[AmbiguousDeclaration]) -> str:
        lines = ["Resolve the following ambiguous CSS declarations:\n"]
        for i, decl in enumerate(ambiguous):
            candidates_str = ", ".join(name for name, _ in decl.candidates)
            lines.append(
                f'{i}. selector="{decl.selector}" '
                f'property="{decl.prop}" '
                f'value="{decl.value}" '
                f'candidates=[{candidates_str}]'
            )
        lines.append("\nReturn a JSON array with your token choice for each index.")
        return "\n".join(lines)

    def _parse_response(self, raw: str, ambiguous: List[AmbiguousDeclaration]) -> Dict[int, str]:
        """Parse AI JSON response into a decisions dict"""
        cleaned = re.sub(r'```(?:json)?\s*', '', raw).replace('```', '').strip()
        data = json.loads(cleaned)

        decisions: Dict[int, str] = {}
        valid_candidates_by_index = {
            i: {name for name, _ in decl.candidates}
            for i, decl in enumerate(ambiguous)
        }

        for entry in data:
            idx = int(entry.get("index", -1))
            token = entry.get("token", "").strip()
            if idx < 0 or idx >= len(ambiguous):
                continue
            if token not in valid_candidates_by_index.get(idx, set()):
                continue
            decisions[idx] = token

        return decisions
