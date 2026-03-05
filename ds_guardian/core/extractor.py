"""
Design System Extractor Module
Consolidates extracted tokens into structured design-system.css output
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


CATEGORY_FILES = {
    "colors": "palette.css",
    "typography": "fonts.css",
    "spacing": "spacing.css",
    "borders": "borders.css",
    "shadows": "shadows.css",
    "motion": "motion.css",
}

CATEGORY_ORDER = ["colors", "typography", "spacing", "borders", "shadows", "motion"]


@dataclass
class DesignToken:
    """A single extracted design token"""
    name: str
    value: str
    category: str
    comment: Optional[str] = None


@dataclass
class ExtractedDesignSystem:
    """Full extracted design system result"""
    tokens_by_category: Dict[str, List[DesignToken]] = field(default_factory=dict)
    existing_vars: List[str] = field(default_factory=list)

    def all_tokens(self) -> List[DesignToken]:
        result = []
        for cat in CATEGORY_ORDER:
            result.extend(self.tokens_by_category.get(cat, []))
        for cat in self.tokens_by_category:
            if cat not in CATEGORY_ORDER:
                result.extend(self.tokens_by_category[cat])
        return result

    def total_count(self) -> int:
        return sum(len(v) for v in self.tokens_by_category.values())


class DesignSystemExtractor:
    """Builds a structured design system from AI-extracted tokens and raw CSS"""

    def collect_existing_vars(self, css_content: str) -> List[str]:
        """
        Find all existing CSS variable declarations (var(--...) usages are ignored;
        we look for --name: value declarations inside :root or any selector).
        """
        pattern = re.compile(r'(--[\w-]+)\s*:\s*([^;}\n]+)', re.MULTILINE)
        seen = {}
        for m in pattern.finditer(css_content):
            name = m.group(1).strip()
            value = m.group(2).strip()
            if name not in seen:
                seen[name] = value
        return [f"{name}: {value};" for name, value in seen.items()]

    def build_design_system_css(self, extracted: ExtractedDesignSystem) -> str:
        """
        Render the full design-system.css content from an ExtractedDesignSystem.
        """
        lines = []

        for cat in CATEGORY_ORDER:
            tokens = extracted.tokens_by_category.get(cat, [])
            if not tokens:
                continue
            lines.append(f"/* {cat.capitalize()} */")
            lines.append(":root {")
            for token in tokens:
                comment = f"  /* {token.comment} */" if token.comment else ""
                lines.append(f"  {token.name}: {token.value};{comment}")
            lines.append("}")
            lines.append("")

        # Extra categories not in the standard order
        for cat, tokens in extracted.tokens_by_category.items():
            if cat in CATEGORY_ORDER or not tokens:
                continue
            lines.append(f"/* {cat.capitalize()} */")
            lines.append(":root {")
            for token in tokens:
                comment = f"  /* {token.comment} */" if token.comment else ""
                lines.append(f"  {token.name}: {token.value};{comment}")
            lines.append("}")
            lines.append("")

        if extracted.existing_vars:
            lines.append("/* Existing tokens */")
            lines.append(":root {")
            for decl in extracted.existing_vars:
                lines.append(f"  {decl}")
            lines.append("}")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def build_category_css(self, category: str, tokens: List[DesignToken]) -> str:
        """Render a single category CSS file."""
        lines = [f"/* {category.capitalize()} */", ":root {"]
        for token in tokens:
            comment = f"  /* {token.comment} */" if token.comment else ""
            lines.append(f"  {token.name}: {token.value};{comment}")
        lines.append("}")
        return "\n".join(lines) + "\n"
