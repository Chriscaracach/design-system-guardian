"""
Design System Analyzer Module
Uses AI to produce qualitative health analysis and concrete improvement proposals
for a CSS design system, based on pre-processed script metrics.
"""

import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ds_guardian.ai.client import BaseAIClient
from ds_guardian.core.value_analyzer import ValueMap
from ds_guardian.core.rules import RefactoringRules


SYSTEM_PROMPT = """You are a senior design systems engineer. You are given:
1. A summary of CSS values found in a codebase (with frequency and usage context)
2. The existing design tokens already defined in design-system.css
3. Script-computed metrics: coverage %, orphaned values, unused tokens, duplicate tokens

Your job is to produce TWO sections:

--- ANALYSIS ---
Observations about the health and quality of the current design system:
- Near-duplicate values that are used interchangeably (e.g. #1a1a1a vs #1c1c1c)
- Token naming inconsistencies (mixing conventions like --btn-blue and --color-primary)
- Scale gaps or discontinuities (e.g. spacing jumps from 8px to 24px with nothing in between)
- Categories that are over-specified or under-specified
- Anti-patterns (mixing px and rem in the same scale, magic numbers, etc.)

--- PROPOSALS ---
Concrete, actionable improvements. Each proposal must be self-contained and specific:
- RENAME: "--old-name" → "--new-name" (reason)
- MERGE: "--token-a" and "--token-b" have the same value — keep "--preferred-name"
- ADD: "--new-token: value" to cover orphaned value used Nx across the codebase
- REMOVE: "--unused-token" is defined but never referenced in the codebase
- RESTRUCTURE: suggest better category grouping if the current structure is fragmented

Be direct and specific. Prioritise by impact (most frequent values / biggest inconsistencies first).
Do not output JSON. Write plain text with the two clearly labelled sections."""


@dataclass
class AnalysisResult:
    """Result from AI design system health analysis"""
    success: bool
    analysis: str = ""
    proposals: str = ""
    tokens_used: int = 0
    error: Optional[str] = None

    @property
    def full_text(self) -> str:
        parts = []
        if self.analysis:
            parts.append(self.analysis)
        if self.proposals:
            parts.append(self.proposals)
        return "\n\n".join(parts)


@dataclass
class ScriptMetrics:
    """Metrics computed by scripts before AI analysis"""
    total_value_occurrences: int = 0
    covered_occurrences: int = 0
    orphaned_values: List[Dict] = field(default_factory=list)    # {value, frequency, properties}
    unused_tokens: List[str] = field(default_factory=list)       # token names
    duplicate_tokens: List[Dict] = field(default_factory=list)   # {value, tokens: [name1, name2]}
    total_tokens_defined: int = 0
    files_analysed: int = 0

    @property
    def coverage_pct(self) -> float:
        if self.total_value_occurrences == 0:
            return 0.0
        return (self.covered_occurrences / self.total_value_occurrences) * 100


class DesignSystemAnalyzer:
    """
    Produces a design-system health report combining script metrics and AI insights.
    """

    def __init__(self, client: BaseAIClient):
        self.client = client

    def compute_metrics(
        self,
        value_map: ValueMap,
        rules: RefactoringRules,
        min_orphan_frequency: int = 3,
    ) -> ScriptMetrics:
        """
        Compute deterministic metrics from the value map and token rules.

        Args:
            value_map: Structured CSS value map from CSSValueAnalyzer
            rules: Parsed design tokens from design-system.css
            min_orphan_frequency: Minimum occurrences to flag a value as orphaned

        Returns:
            ScriptMetrics with coverage, orphans, unused tokens, and duplicates
        """
        metrics = ScriptMetrics()
        metrics.total_tokens_defined = rules.get_token_count()

        # Build normalised token value → name(s) map
        token_value_index: Dict[str, List[str]] = {}
        for name, value in {**rules.colors, **rules.spacing, **rules.typography,
                             **rules.borders, **rules.shadows, **rules.breakpoints}.items():
            key = _norm(value)
            token_value_index.setdefault(key, []).append(name)
        for _cat, tokens in rules.custom.items():
            for name, value in tokens.items():
                key = _norm(value)
                token_value_index.setdefault(key, []).append(name)

        # Coverage: count occurrences that have a matching token
        for usage in value_map.usages.values():
            metrics.total_value_occurrences += usage.frequency
            if _norm(usage.value) in token_value_index:
                metrics.covered_occurrences += usage.frequency
            elif usage.frequency >= min_orphan_frequency:
                metrics.orphaned_values.append({
                    "value": usage.value,
                    "frequency": usage.frequency,
                    "properties": list(usage.top_properties(2)),
                })

        # Duplicate tokens: same value → multiple token names
        for value_key, names in token_value_index.items():
            if len(names) > 1:
                metrics.duplicate_tokens.append({"value": value_key, "tokens": names})

        # Unused tokens: token value never appears in the value map
        all_token_names = set()
        for name in {**rules.colors, **rules.spacing, **rules.typography,
                      **rules.borders, **rules.shadows, **rules.breakpoints}:
            all_token_names.add(name)
        for _cat, tokens in rules.custom.items():
            for name in tokens:
                all_token_names.add(name)

        used_values = {_norm(u.value) for u in value_map.usages.values()}
        for name, value in {**rules.colors, **rules.spacing, **rules.typography,
                              **rules.borders, **rules.shadows, **rules.breakpoints}.items():
            if _norm(value) not in used_values:
                metrics.unused_tokens.append(name)

        # Sort orphans by frequency descending
        metrics.orphaned_values.sort(key=lambda x: x["frequency"], reverse=True)

        return metrics

    def analyse(
        self,
        value_map: ValueMap,
        rules: RefactoringRules,
        metrics: ScriptMetrics,
    ) -> AnalysisResult:
        """
        Run AI analysis and generate proposals.

        Args:
            value_map: Structured CSS value map
            rules: Parsed design tokens
            metrics: Pre-computed script metrics

        Returns:
            AnalysisResult with analysis text and proposals
        """
        prompt = self._build_prompt(value_map, rules, metrics)
        response = self.client.generate(prompt, system=SYSTEM_PROMPT)

        if "error" in response:
            return AnalysisResult(success=False, error=response["error"])

        raw = response.get("response", "").strip()
        if not raw:
            return AnalysisResult(success=False, error="Empty response from AI")

        tokens_used = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)

        analysis, proposals = self._split_sections(raw)
        return AnalysisResult(
            success=True,
            analysis=analysis,
            proposals=proposals,
            tokens_used=tokens_used,
        )

    def _build_prompt(
        self,
        value_map: ValueMap,
        rules: RefactoringRules,
        metrics: ScriptMetrics,
    ) -> str:
        lines = ["=== SCRIPT METRICS ==="]
        lines.append(f"Coverage: {metrics.coverage_pct:.1f}% of hardcoded value occurrences have a matching token")
        lines.append(f"Tokens defined: {metrics.total_tokens_defined}")
        lines.append(f"Unused tokens: {len(metrics.unused_tokens)}")
        lines.append(f"Duplicate tokens: {len(metrics.duplicate_tokens)}")
        lines.append(f"Orphaned values (no token, freq >= 3): {len(metrics.orphaned_values)}")

        if metrics.unused_tokens:
            lines.append("\nUnused tokens (defined but never found in codebase):")
            for name in metrics.unused_tokens[:20]:
                lines.append(f"  {name}")

        if metrics.duplicate_tokens:
            lines.append("\nDuplicate tokens (same value, different names):")
            for dup in metrics.duplicate_tokens[:10]:
                lines.append(f"  value={dup['value']} → {', '.join(dup['tokens'])}")

        if metrics.orphaned_values:
            lines.append("\nTop orphaned values (hardcoded, no token):")
            for o in metrics.orphaned_values[:20]:
                lines.append(f"  value={o['value']} freq={o['frequency']} props={o['properties']}")

        lines.append("\n=== EXISTING TOKENS ===")
        from ds_guardian.core.rules import RulesParser
        token_lines = RulesParser.__new__(RulesParser)
        token_text = _format_token_list(rules)
        lines.append(token_text)

        lines.append("\n=== CSS VALUE SUMMARY (top 100 by frequency) ===")
        lines.append(value_map.format_for_prompt(max_values=100))

        lines.append("\nNow produce the ANALYSIS and PROPOSALS sections.")
        return "\n".join(lines)

    def _split_sections(self, raw: str):
        """Split AI response into analysis and proposals sections."""
        analysis = ""
        proposals = ""

        analysis_markers = ["--- analysis ---", "## analysis", "# analysis", "**analysis**"]
        proposals_markers = ["--- proposals ---", "## proposals", "# proposals", "**proposals**"]

        lower = raw.lower()

        analysis_pos = -1
        for marker in analysis_markers:
            p = lower.find(marker)
            if p != -1:
                analysis_pos = p + len(marker)
                break

        proposals_pos = -1
        for marker in proposals_markers:
            p = lower.find(marker)
            if p != -1:
                proposals_pos = p + len(marker)
                break

        if analysis_pos != -1 and proposals_pos != -1:
            if analysis_pos < proposals_pos:
                analysis = raw[analysis_pos:proposals_pos].strip()
                proposals = raw[proposals_pos:].strip()
            else:
                proposals = raw[proposals_pos:analysis_pos].strip()
                analysis = raw[analysis_pos:].strip()
        elif analysis_pos != -1:
            analysis = raw[analysis_pos:].strip()
        elif proposals_pos != -1:
            proposals = raw[proposals_pos:].strip()
        else:
            # No clear sections — treat entire response as analysis
            analysis = raw.strip()

        return analysis, proposals


def _norm(value: str) -> str:
    """Normalise a CSS value for comparison"""
    v = value.strip().lower()
    m = re.match(r'^#([0-9a-f]{3})$', v)
    if m:
        r, g, b = m.group(1)
        v = f'#{r}{r}{g}{g}{b}{b}'
    return v


def _format_token_list(rules: RefactoringRules) -> str:
    """Format all tokens as a compact text list"""
    lines = []
    for name, value in rules.colors.items():
        lines.append(f"  {name}: {value}  [color]")
    for name, value in rules.spacing.items():
        lines.append(f"  {name}: {value}  [spacing]")
    for name, value in rules.typography.items():
        lines.append(f"  {name}: {value}  [typography]")
    for name, value in rules.borders.items():
        lines.append(f"  {name}: {value}  [border]")
    for name, value in rules.shadows.items():
        lines.append(f"  {name}: {value}  [shadow]")
    for name, value in rules.breakpoints.items():
        lines.append(f"  {name}: {value}  [breakpoint]")
    for cat, tokens in rules.custom.items():
        for name, value in tokens.items():
            lines.append(f"  {name}: {value}  [{cat}]")
    return "\n".join(lines) if lines else "  (no tokens defined)"
