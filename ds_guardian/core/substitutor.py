"""
CSS Substitutor Module
Performs deterministic exact-match substitution of CSS values with design tokens.
Identifies ambiguous cases (same value → multiple token candidates) for AI resolution.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ds_guardian.core.rules import RefactoringRules


@dataclass
class AmbiguousDeclaration:
    """A CSS declaration where the value matches multiple token candidates"""
    selector: str
    prop: str
    value: str
    candidates: List[Tuple[str, str]]  # list of (token_name, token_value)
    line_number: int = 0


@dataclass
class SubstitutionResult:
    """Result of the script substitution phase"""
    css: str                                          # CSS after exact substitutions applied
    substitution_count: int = 0                       # Number of values replaced by script
    ambiguous: List[AmbiguousDeclaration] = field(default_factory=list)

    @property
    def has_ambiguous(self) -> bool:
        return len(self.ambiguous) > 0

    @property
    def has_changes(self) -> bool:
        return self.substitution_count > 0 or self.has_ambiguous


class CSSSubstitutor:
    """
    Phase 1 of the refactor pipeline.

    For each CSS value declaration:
      - 1 token match  → replace immediately (no AI needed)
      - 0 token matches → leave as-is
      - 2+ token matches → mark as ambiguous for AI resolution
    """

    # Matches a property: value; declaration (captures indentation for round-trip fidelity)
    _DECL_RE = re.compile(
        r'^(?P<indent>\s*)(?P<prop>[\w-]+)\s*:\s*(?P<value>[^;{}\n]+?)\s*;(?P<tail>[^\n]*)',
        re.MULTILINE
    )

    def __init__(self, rules: RefactoringRules):
        self._rules = rules
        # Build reverse map: normalised_value → [(token_name, original_value), ...]
        self._value_to_tokens: Dict[str, List[Tuple[str, str]]] = {}
        self._build_index()

    def _build_index(self):
        """Build a reverse index from token value → token name(s)"""
        all_dicts = [
            self._rules.colors,
            self._rules.spacing,
            self._rules.typography,
            self._rules.borders,
            self._rules.shadows,
            self._rules.breakpoints,
        ]
        for d in all_dicts:
            for name, value in d.items():
                key = _normalise(value)
                if key not in self._value_to_tokens:
                    self._value_to_tokens[key] = []
                self._value_to_tokens[key].append((name, value))

        for _cat, tokens in self._rules.custom.items():
            for name, value in tokens.items():
                key = _normalise(value)
                if key not in self._value_to_tokens:
                    self._value_to_tokens[key] = []
                self._value_to_tokens[key].append((name, value))

    def substitute(self, css_content: str) -> SubstitutionResult:
        """
        Apply deterministic substitutions and collect ambiguous declarations.

        Returns a SubstitutionResult with the partially-rewritten CSS and any
        ambiguous declarations that need AI resolution.
        """
        result_chars = list(css_content)
        substitution_count = 0
        ambiguous: List[AmbiguousDeclaration] = []

        # Track current selector context by scanning line by line
        current_selector = ''
        selector_stack: List[str] = []

        # We do two passes:
        # Pass 1: find all declarations and decide what to do with each
        # Pass 2: apply substitutions in reverse order (to preserve offsets)

        replacements: List[Tuple[int, int, str]] = []  # (start, end, replacement)

        for m in self._DECL_RE.finditer(css_content):
            prop = m.group('prop').strip().lower()
            raw_value = m.group('value').strip()

            # Skip values that are already CSS variables
            if 'var(' in raw_value:
                continue

            # Try to find the current selector by looking backwards from this match
            selector = _find_selector(css_content, m.start())

            matches = self._lookup(raw_value)

            if len(matches) == 1:
                # Deterministic — replace value with var(--token-name)
                token_name = matches[0][0]
                new_value = f'var({token_name})'
                # Build replacement string preserving indent, prop, tail
                old_decl = m.group(0)
                new_decl = (
                    f"{m.group('indent')}{m.group('prop')}: {new_value};"
                    f"{m.group('tail')}"
                )
                if old_decl != new_decl:
                    replacements.append((m.start(), m.end(), new_decl))
                    substitution_count += 1

            elif len(matches) > 1:
                # Ambiguous — flag for AI
                line_no = css_content[:m.start()].count('\n') + 1
                ambiguous.append(AmbiguousDeclaration(
                    selector=selector,
                    prop=prop,
                    value=raw_value,
                    candidates=matches,
                    line_number=line_no,
                ))

        # Apply replacements in reverse order so offsets stay valid
        output = css_content
        for start, end, new_text in sorted(replacements, key=lambda r: r[0], reverse=True):
            output = output[:start] + new_text + output[end:]

        return SubstitutionResult(
            css=output,
            substitution_count=substitution_count,
            ambiguous=ambiguous,
        )

    def apply_ai_decisions(
        self,
        css: str,
        decisions: Dict[int, str],
        ambiguous: List[AmbiguousDeclaration],
    ) -> str:
        """
        Apply AI decisions for ambiguous declarations.

        Args:
            css: CSS after script substitution phase
            decisions: mapping of ambiguous index → chosen token name
            ambiguous: the list of AmbiguousDeclaration from substitute()

        Returns:
            Final CSS with all substitutions applied
        """
        if not decisions:
            return css

        replacements: List[Tuple[int, int, str]] = []

        for idx, token_name in decisions.items():
            if idx >= len(ambiguous):
                continue
            decl = ambiguous[idx]
            new_value = f'var({token_name})'

            # Find and replace the specific declaration in the CSS
            pattern = re.compile(
                r'((?:^|\n)\s*' + re.escape(decl.prop) + r'\s*:\s*)' +
                re.escape(decl.value) + r'(\s*;)',
                re.MULTILINE
            )
            css = pattern.sub(r'\g<1>' + new_value + r'\g<2>', css, count=1)

        return css

    def _lookup(self, value: str) -> List[Tuple[str, str]]:
        """Look up a value in the token index, returning all matches"""
        return self._value_to_tokens.get(_normalise(value), [])


def _normalise(value: str) -> str:
    """Normalise a CSS value for comparison"""
    v = value.strip().lower()
    # Expand 3-digit hex to 6-digit
    m = re.match(r'^#([0-9a-f]{3})$', v)
    if m:
        r, g, b = m.group(1)
        v = f'#{r}{r}{g}{g}{b}{b}'
    return v


def _find_selector(css: str, pos: int) -> str:
    """
    Walk backwards from pos to find the opening brace and the selector before it.
    Returns the selector string or empty string if not found.
    """
    # Find the most recent '{' before pos
    brace_pos = css.rfind('{', 0, pos)
    if brace_pos == -1:
        return ''

    # Grab the text before that brace and strip to find selector
    before = css[:brace_pos].strip()
    # Take the last line (or last non-empty segment)
    lines = [l.strip() for l in before.splitlines() if l.strip()]
    if lines:
        return lines[-1]
    return ''
