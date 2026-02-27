"""
Prompt Optimizer Module
Analyzes CSS content and filters relevant design tokens to reduce prompt size
"""

import re
from typing import Dict, List, Set
from ds_guardian.core.rules import RefactoringRules, DesignToken


class PromptOptimizer:
    """Optimizes prompts by filtering relevant design tokens"""
    
    def __init__(self):
        """Initialize optimizer"""
        pass
    
    def extract_css_values(self, css_content: str) -> Dict[str, Set[str]]:
        """
        Extract values from CSS that might match design tokens
        
        Args:
            css_content: CSS content to analyze
        
        Returns:
            Dictionary mapping value types to sets of values
        """
        values = {
            'colors': set(),
            'spacing': set(),
            'typography': set(),
            'borders': set(),
            'shadows': set()
        }
        
        # Extract hex colors
        hex_colors = re.findall(r'#[0-9a-fA-F]{3,8}\b', css_content)
        values['colors'].update(hex_colors)
        
        # Extract rgb/rgba colors
        rgb_colors = re.findall(r'rgba?\([^)]+\)', css_content)
        values['colors'].update(rgb_colors)
        
        # Extract pixel values (spacing, font sizes, borders)
        px_values = re.findall(r'\b\d+px\b', css_content)
        values['spacing'].update(px_values)
        
        # Extract rem/em values
        rem_values = re.findall(r'\b\d+\.?\d*(?:rem|em)\b', css_content)
        values['typography'].update(rem_values)
        
        # Extract font weights
        font_weights = re.findall(r'font-weight:\s*(\d+|normal|bold|lighter|bolder)', css_content)
        values['typography'].update(font_weights)
        
        # Extract font sizes
        font_sizes = re.findall(r'font-size:\s*([^;]+)', css_content)
        values['typography'].update([fs.strip() for fs in font_sizes])
        
        # Extract border radius values
        border_radius = re.findall(r'border-radius:\s*([^;]+)', css_content)
        values['borders'].update([br.strip() for br in border_radius])
        
        # Extract box shadows
        shadows = re.findall(r'box-shadow:\s*([^;]+)', css_content)
        values['shadows'].update([s.strip() for s in shadows])
        
        return values
    
    def filter_relevant_tokens(self, css_content: str, rules: RefactoringRules) -> RefactoringRules:
        """
        Filter design tokens to only include those relevant to the CSS content
        
        Args:
            css_content: CSS content to analyze
            rules: All available design tokens
        
        Returns:
            Filtered RefactoringRules with only relevant tokens
        """
        # Extract values from CSS
        css_values = self.extract_css_values(css_content)
        
        # Create filtered rules
        filtered = RefactoringRules()
        
        # Filter colors - check if any color value is close to a token value
        for name, value in rules.colors.items():
            if self._is_color_relevant(value, css_values['colors']):
                filtered.colors[name] = value
        
        # Filter spacing - check if any spacing value matches
        for name, value in rules.spacing.items():
            if self._is_spacing_relevant(value, css_values['spacing']):
                filtered.spacing[name] = value
        
        # Filter typography - check if any typography value matches
        for name, value in rules.typography.items():
            if self._is_typography_relevant(value, css_values['typography']):
                filtered.typography[name] = value
        
        # Filter borders - check if any border value matches
        for name, value in rules.borders.items():
            if self._is_border_relevant(value, css_values['borders']):
                filtered.borders[name] = value
        
        # Filter shadows - always include shadows if CSS has any
        if css_values['shadows']:
            filtered.shadows = rules.shadows.copy()
        
        # Always include breakpoints (small set)
        filtered.breakpoints = rules.breakpoints.copy()
        
        # Copy custom tokens
        filtered.custom = rules.custom.copy()
        
        return filtered
    
    def _is_color_relevant(self, token_value: str, css_colors: Set[str]) -> bool:
        """Check if a color token is relevant to CSS content"""
        # Normalize token value
        token_lower = token_value.lower().strip()
        
        # Check direct match
        if token_lower in css_colors:
            return True
        
        # Check if it's a hex color in the CSS
        for css_color in css_colors:
            if css_color.lower() == token_lower:
                return True
        
        return False
    
    def _is_spacing_relevant(self, token_value: str, css_spacing: Set[str]) -> bool:
        """Check if a spacing token is relevant to CSS content"""
        # Extract numeric value from token
        token_lower = token_value.lower().strip()
        
        # Check direct match
        if token_lower in css_spacing:
            return True
        
        # Check if the numeric part matches
        token_match = re.search(r'(\d+(?:\.\d+)?)', token_value)
        if token_match:
            token_num = token_match.group(1)
            for css_val in css_spacing:
                if token_num in css_val:
                    return True
        
        return False
    
    def _is_typography_relevant(self, token_value: str, css_typography: Set[str]) -> bool:
        """Check if a typography token is relevant to CSS content"""
        token_lower = token_value.lower().strip()
        
        # Check direct match
        if token_lower in css_typography:
            return True
        
        # Check partial matches for font weights and sizes
        for css_val in css_typography:
            if token_lower in css_val.lower() or css_val.lower() in token_lower:
                return True
        
        return False
    
    def _is_border_relevant(self, token_value: str, css_borders: Set[str]) -> bool:
        """Check if a border token is relevant to CSS content"""
        token_lower = token_value.lower().strip()
        
        # Check direct match
        if token_lower in css_borders:
            return True
        
        # Check if the value appears in any border declaration
        for css_val in css_borders:
            if token_lower in css_val.lower():
                return True
        
        return False
    
    def get_optimization_stats(self, original: RefactoringRules, filtered: RefactoringRules) -> Dict[str, int]:
        """
        Get statistics about the optimization
        
        Args:
            original: Original rules
            filtered: Filtered rules
        
        Returns:
            Dictionary with optimization statistics
        """
        return {
            'original_tokens': original.get_token_count(),
            'filtered_tokens': filtered.get_token_count(),
            'reduction_percent': int((1 - filtered.get_token_count() / max(original.get_token_count(), 1)) * 100),
            'colors_kept': len(filtered.colors),
            'spacing_kept': len(filtered.spacing),
            'typography_kept': len(filtered.typography)
        }
