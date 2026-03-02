"""
Rules Parser Module
Parses rules.md file and extracts design system rules
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
    """Parses rules.md file"""
    
    # Category mappings
    CATEGORY_KEYWORDS = {
        'color': ['color', 'colour', 'palette'],
        'spacing': ['spacing', 'space', 'margin', 'padding', 'gap'],
        'typography': ['typography', 'font', 'text', 'type'],
        'border': ['border', 'outline', 'stroke'],
        'shadow': ['shadow', 'elevation', 'depth'],
        'breakpoint': ['breakpoint', 'media', 'responsive', 'screen']
    }
    
    def __init__(self, rules_file: str = 'rules.md'):
        """
        Initialize parser
        
        Args:
            rules_file: Path to rules.md file
        """
        self.rules_file = Path(rules_file)
        
        if not self.rules_file.exists():
            raise FileNotFoundError(f"Rules file not found: {self.rules_file}")
    
    def parse(self) -> RefactoringRules:
        """
        Parse rules file
        
        Returns:
            RefactoringRules object
        """
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        rules = RefactoringRules()
        current_category = None
        current_section = None
        
        lines = content.split('\n')
        in_code_fence = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('<!--'):
                continue
            
            # Track fenced code blocks — toggle on opening/closing ```
            if line.startswith('```'):
                in_code_fence = not in_code_fence
                continue
            
            # Check for headers (only outside code fences)
            if not in_code_fence and line.startswith('#'):
                header_text = line.lstrip('#').strip().lower()
                current_category = self._detect_category(header_text)
                current_section = header_text
                continue
            
            # Parse token definitions (works inside and outside code fences)
            # Format: --token-name: value
            # or: token-name: value
            token_match = re.match(r'^(--)?([\w-]+):\s*(.+)$', line)
            if token_match:
                prefix, name, value = token_match.groups()
                
                # Clean up value (remove comments, trailing semicolons)
                value = value.split('//')[0].split('/*')[0].strip()
                value = value.rstrip(';').strip()
                
                if not value:
                    continue
                
                # Add prefix if not present
                if not prefix:
                    name = f'--{name}'
                else:
                    name = f'{prefix}{name}'
                
                # Store in appropriate category
                if current_category:
                    self._add_token(rules, current_category, name, value)
                elif current_section:
                    # Store in custom category
                    if current_section not in rules.custom:
                        rules.custom[current_section] = {}
                    rules.custom[current_section][name] = value
        
        return rules
    
    def _detect_category(self, header_text: str) -> Optional[str]:
        """Detect category from header text"""
        header_lower = header_text.lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(keyword in header_lower for keyword in keywords):
                return category
        
        return None
    
    def _add_token(self, rules: RefactoringRules, category: str, name: str, value: str):
        """Add token to appropriate category"""
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
    
    def generate_prompt_context(self, rules: RefactoringRules) -> str:
        """
        Generate context string for AI prompt
        
        Args:
            rules: RefactoringRules object
        
        Returns:
            Formatted string for AI prompt
        """
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
