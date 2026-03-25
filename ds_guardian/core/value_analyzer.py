"""
Value Analyzer Module
Pre-processes CSS files into a structured value map for AI and script use.
Replaces raw CSS blobs as input to AI — deterministic, fast, zero AI cost.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path


SKIP_VALUES: Set[str] = {
    '0', 'none', 'auto', 'inherit', 'initial', 'unset', 'revert',
    'normal', 'bold', 'italic', 'transparent', 'currentcolor', 'currentColor',
    'relative', 'absolute', 'fixed', 'sticky', 'static',
    'block', 'inline', 'inline-block', 'flex', 'grid', 'inline-flex', 'inline-grid',
    'hidden', 'visible', 'collapse',
    'center', 'left', 'right', 'top', 'bottom',
    'uppercase', 'lowercase', 'capitalize', 'nowrap', 'wrap',
    'pointer', 'default', 'text', 'move',
    'solid', 'dashed', 'dotted', 'double',
    'serif', 'sans-serif', 'monospace',
    'cover', 'contain', 'no-repeat', 'repeat',
    '100%', '50%',
}


@dataclass
class ValueUsage:
    """Tracks where and how a CSS value is used across the codebase"""
    value: str
    frequency: int = 0
    properties: Dict[str, int] = field(default_factory=dict)
    selectors: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    code_examples: List[Dict[str, str]] = field(default_factory=list)

    def add_occurrence(self, prop: str, selector: str, file_path: str, code_snippet: str = ""):
        self.frequency += 1
        self.properties[prop] = self.properties.get(prop, 0) + 1
        if selector and selector not in self.selectors:
            self.selectors.append(selector)
        if file_path not in self.files:
            self.files.append(file_path)
        if code_snippet and len(self.code_examples) < 5:
            self.code_examples.append({
                "file": file_path,
                "selector": selector,
                "property": prop,
                "snippet": code_snippet
            })

    def top_properties(self, n: int = 3) -> List[str]:
        return sorted(self.properties, key=lambda p: self.properties[p], reverse=True)[:n]

    def format_for_prompt(self, include_examples: bool = False) -> str:
        props = ", ".join(
            f"{p} ({c}x)" for p, c in
            sorted(self.properties.items(), key=lambda x: x[1], reverse=True)[:3]
        )
        selectors_preview = ", ".join(self.selectors[:3])
        base = (
            f'value="{self.value}" '
            f'frequency={self.frequency} '
            f'properties=[{props}] '
            f'selectors=[{selectors_preview}]'
        )
        if include_examples and self.code_examples:
            examples = "\n  Examples:"
            for ex in self.code_examples[:3]:
                examples += f"\n    {ex['file']}: {ex['selector']} {{ {ex['property']}: {self.value}; }}"
            return base + examples
        return base


@dataclass
class ValueMap:
    """Complete structured map of all values found in a CSS codebase"""
    usages: Dict[str, ValueUsage] = field(default_factory=dict)

    def add(self, value: str, prop: str, selector: str, file_path: str, code_snippet: str = ""):
        normalised = _normalise_value(value)
        if normalised not in self.usages:
            self.usages[normalised] = ValueUsage(value=normalised)
        self.usages[normalised].add_occurrence(prop, selector, file_path, code_snippet)

    def get(self, value: str) -> Optional[ValueUsage]:
        return self.usages.get(_normalise_value(value))

    def frequent_values(self, min_frequency: int = 2) -> List[ValueUsage]:
        return sorted(
            [u for u in self.usages.values() if u.frequency >= min_frequency],
            key=lambda u: u.frequency,
            reverse=True
        )

    def format_for_prompt(self, max_values: int = 200) -> str:
        """Serialise the value map into a compact text format for AI prompts"""
        lines = []
        sorted_usages = sorted(
            self.usages.values(),
            key=lambda u: u.frequency,
            reverse=True
        )[:max_values]
        for usage in sorted_usages:
            lines.append(usage.format_for_prompt())
        return "\n".join(lines)


def _split_shorthand(prop: str, value: str) -> List[str]:
    """
    For shorthand properties (margin, padding, border), attempt to split into
    individual values. For non-shorthands, return the value as a single-item list.
    """
    simple_shorthands = {'margin', 'padding', 'gap'}
    if prop in simple_shorthands:
        parts = value.split()
        return [p.strip() for p in parts if p.strip()]
    return [value.strip()]


def _normalise_value(value: str) -> str:
    """Normalise a CSS value for consistent comparison"""
    v = value.strip().lower()
    # Normalise hex colors to 6-digit lowercase
    m = re.match(r'^#([0-9a-f]{3})$', v)
    if m:
        r, g, b = m.group(1)
        v = f'#{r}{r}{g}{g}{b}{b}'
    return v


def _should_skip(value: str) -> bool:
    """Return True if the value is not a candidate design token"""
    v = value.strip()
    if not v:
        return True
    # Skip CSS variables (already tokenised)
    if v.startswith('var('):
        return True
    # Skip plain keywords
    if v.lower() in {s.lower() for s in SKIP_VALUES}:
        return True
    # Skip single integers (line-height: 1, z-index: 10, etc.) below threshold
    if re.match(r'^\d+$', v) and int(v) < 50:
        return True
    # Skip percentages that are 100% or common layout percentages
    if re.match(r'^\d+%$', v) and int(v[:-1]) in {100, 50, 25, 75, 33, 66}:
        return True
    return False


# Properties whose values are worth tracking as potential tokens
TRACKABLE_PROPERTIES = {
    'color', 'background-color', 'background', 'border-color',
    'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
    'outline-color', 'fill', 'stroke', 'text-decoration-color', 'caret-color',
    'font-size', 'font-weight', 'font-family', 'line-height', 'letter-spacing',
    'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'gap', 'row-gap', 'column-gap',
    'width', 'height', 'min-width', 'max-width', 'min-height', 'max-height',
    'border-radius', 'border-top-left-radius', 'border-top-right-radius',
    'border-bottom-left-radius', 'border-bottom-right-radius',
    'border-width', 'border', 'border-top', 'border-right', 'border-bottom', 'border-left',
    'outline', 'outline-width',
    'box-shadow', 'text-shadow', 'filter', 'backdrop-filter',
    'transition', 'animation', 'animation-duration', 'transition-duration',
    'opacity', 'z-index',
}


class CSSValueAnalyzer:
    """
    Extracts all meaningful CSS values from a set of CSS files and builds
    a structured ValueMap with frequency and context data.
    """

    # Match a CSS rule block: selector { ... }
    _RULE_RE = re.compile(
        r'([^{}@/][^{}]*?)\{([^{}]*?)\}',
        re.DOTALL
    )

    # Match a single property declaration inside a rule
    _DECL_RE = re.compile(
        r'([\w-]+)\s*:\s*([^;}\n]+)',
        re.MULTILINE
    )

    def analyze_files(self, files) -> ValueMap:
        """
        Analyze a list of StyleFile objects and return a ValueMap.

        Args:
            files: List of StyleFile objects (from FileScanner)

        Returns:
            Populated ValueMap
        """
        value_map = ValueMap()
        for f in files:
            try:
                content = Path(f.path).read_text(encoding='utf-8')
                self._analyze_content(content, str(f.relative_path), value_map)
            except Exception:
                continue
        return value_map

    def analyze_content(self, css_content: str, source: str = '<inline>') -> ValueMap:
        """Analyze a single CSS string and return a ValueMap."""
        value_map = ValueMap()
        self._analyze_content(css_content, source, value_map)
        return value_map

    def _analyze_content(self, css_content: str, source: str, value_map: ValueMap):
        """Parse CSS content and populate the value_map in place."""
        # Strip comments first
        content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)

        for rule_match in self._RULE_RE.finditer(content):
            selector = rule_match.group(1).strip()
            # Clean up the selector (take last meaningful segment)
            selector = selector.splitlines()[-1].strip()

            body = rule_match.group(2)
            for decl_match in self._DECL_RE.finditer(body):
                prop = decl_match.group(1).strip().lower()
                raw_value = decl_match.group(2).strip()

                if prop not in TRACKABLE_PROPERTIES:
                    continue

                # Expand shorthand values where possible, otherwise use as-is
                sub_values = _split_shorthand(prop, raw_value)
                for val in sub_values:
                    if not _should_skip(val):
                        # Create a code snippet showing the actual CSS declaration
                        snippet = f"{prop}: {raw_value}"
                        value_map.add(val, prop, selector, source, snippet)
