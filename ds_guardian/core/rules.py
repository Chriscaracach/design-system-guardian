"""
Rules Parser Module
Parses design_system.css and extracts design system tokens
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class DesignToken:
    """Represents a design token (color, spacing, etc.)"""
    name: str
    value: str
    category: str

    def __str__(self):
        return f"{self.name}: {self.value}"


@dataclass
class RefactoringRules:
    """Container for all refactoring rules"""
    colors: Dict[str, str] = field(default_factory=dict)
    spacing: Dict[str, str] = field(default_factory=dict)
    typography: Dict[str, str] = field(default_factory=dict)
    borders: Dict[str, str] = field(default_factory=dict)
    shadows: Dict[str, str] = field(default_factory=dict)
    breakpoints: Dict[str, str] = field(default_factory=dict)
    custom: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def get_all_tokens(self) -> List[DesignToken]:
        """Get all design tokens as a flat list"""
        tokens = []
        for name, value in self.colors.items():
            tokens.append(DesignToken(name, value, 'color'))
        for name, value in self.spacing.items():
            tokens.append(DesignToken(name, value, 'spacing'))
        for name, value in self.typography.items():
            tokens.append(DesignToken(name, value, 'typography'))
        for name, value in self.borders.items():
            tokens.append(DesignToken(name, value, 'border'))
        for name, value in self.shadows.items():
            tokens.append(DesignToken(name, value, 'shadow'))
        for name, value in self.breakpoints.items():
            tokens.append(DesignToken(name, value, 'breakpoint'))
        for category, items in self.custom.items():
            for name, value in items.items():
                tokens.append(DesignToken(name, value, category))
        return tokens

    def get_token_count(self) -> int:
        """Get total number of design tokens"""
        return len(self.get_all_tokens())


class RulesParser:
    """Parses design_system.css — a plain CSS file with :root {} blocks and /* Category */ comments"""

    CATEGORY_KEYWORDS = {
        'color': ['color', 'colour', 'palette'],
        'spacing': ['spacing', 'space', 'margin', 'padding', 'gap'],
        'typography': ['typography', 'font', 'text', 'type'],
        'border': ['border', 'outline', 'stroke', 'radius'],
        'shadow': ['shadow', 'elevation', 'depth'],
        'breakpoint': ['breakpoint', 'media', 'responsive', 'screen'],
        'motion': ['motion', 'transition', 'animation'],
    }

    def __init__(self, rules_file: str = 'design_system.css'):
        self.rules_file = Path(rules_file)
        if not self.rules_file.exists():
            raise FileNotFoundError(f"Design system file not found: {self.rules_file}")

    def parse(self) -> RefactoringRules:
        """Parse design_system.css and return RefactoringRules"""
        content = self.rules_file.read_text(encoding='utf-8')
        rules = RefactoringRules()
        current_category: Optional[str] = None
        current_section: Optional[str] = None

        for line in content.splitlines():
            stripped = line.strip()

            if not stripped:
                continue

            # /* Category name */ comment → new section header
            comment_match = re.match(r'^/\*+\s*(.+?)\s*\*+/$', stripped)
            if comment_match:
                header_text = comment_match.group(1).lower()
                # Skip "existing tokens" section — not used for refactoring
                if 'existing' in header_text:
                    current_category = None
                    current_section = None
                else:
                    current_category = self._detect_category(header_text)
                    current_section = header_text
                continue

            # Skip :root { and } lines
            if re.match(r'^:root\s*\{', stripped) or stripped == '}':
                continue

            # --name: value;
            token_match = re.match(r'^(--[\w-]+)\s*:\s*(.+?)\s*;?\s*(?:/\*.*\*/)?$', stripped)
            if token_match:
                name = token_match.group(1)
                value = token_match.group(2).strip().rstrip(';').strip()
                if not value:
                    continue
                if current_category:
                    self._add_token(rules, current_category, name, value)
                elif current_section:
                    if current_section not in rules.custom:
                        rules.custom[current_section] = {}
                    rules.custom[current_section][name] = value

        return rules

    def _detect_category(self, header_text: str) -> Optional[str]:
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in header_text for kw in keywords):
                return category
        return None

    def _add_token(self, rules: RefactoringRules, category: str, name: str, value: str):
        if category == 'color':
            rules.colors[name] = value
        elif category == 'spacing':
            rules.spacing[name] = value
        elif category == 'typography':
            rules.typography[name] = value
        elif category == 'border':
            rules.borders[name] = value
        elif category == 'shadow':
            rules.shadows[name] = value
        elif category == 'breakpoint':
            rules.breakpoints[name] = value
        elif category == 'motion':
            if 'motion' not in rules.custom:
                rules.custom['motion'] = {}
            rules.custom['motion'][name] = value

    def generate_prompt_context(self, rules: RefactoringRules) -> str:
        """Generate context string for AI prompt"""
        sections = []
        if rules.colors:
            sections.append("COLORS:")
            for name, value in rules.colors.items():
                sections.append(f"  {name}: {value}")
        if rules.spacing:
            sections.append("\nSPACING:")
            for name, value in rules.spacing.items():
                sections.append(f"  {name}: {value}")
        if rules.typography:
            sections.append("\nTYPOGRAPHY:")
            for name, value in rules.typography.items():
                sections.append(f"  {name}: {value}")
        if rules.borders:
            sections.append("\nBORDERS:")
            for name, value in rules.borders.items():
                sections.append(f"  {name}: {value}")
        if rules.shadows:
            sections.append("\nSHADOWS:")
            for name, value in rules.shadows.items():
                sections.append(f"  {name}: {value}")
        if rules.breakpoints:
            sections.append("\nBREAKPOINTS:")
            for name, value in rules.breakpoints.items():
                sections.append(f"  {name}: {value}")
        if rules.custom:
            for category, tokens in rules.custom.items():
                sections.append(f"\n{category.upper()}:")
                for name, value in tokens.items():
                    sections.append(f"  {name}: {value}")
        return '\n'.join(sections)
