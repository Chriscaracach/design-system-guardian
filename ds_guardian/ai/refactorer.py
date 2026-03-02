"""
CSS Refactorer Module
Handles CSS refactoring using AI
"""

import re
from ds_guardian.ai.client import OllamaClient, RefactoringResult


class CSSRefactorer:
    """Handles CSS refactoring using AI"""
    
    SYSTEM_PROMPT = """You are a CSS refactoring expert. Your job is to refactor CSS code to use design system tokens (CSS variables).

Rules:
1. Replace hardcoded values with CSS variables where appropriate
2. Maintain the exact same visual output
3. Preserve all selectors, properties, and structure
4. Only change values to use variables
5. Do not add comments or explanations
6. Return ONLY the refactored CSS, nothing else
7. If a value doesn't match any design token, leave it as-is
8. Be conservative - only replace values that clearly match design tokens

Output format:
- Return the complete refactored CSS
- No markdown code blocks
- No explanations or comments
- Just the raw CSS code"""
    
    def __init__(self, client: OllamaClient):
        """
        Initialize refactorer
        
        Args:
            client: OllamaClient instance
        """
        self.client = client
    
    def refactor(self, css_content: str, design_tokens: str) -> RefactoringResult:
        """
        Refactor CSS using design tokens
        
        Args:
            css_content: Original CSS content
            design_tokens: Design tokens context string
        
        Returns:
            RefactoringResult object
        """
        if not css_content.strip():
            return RefactoringResult(
                success=False,
                refactored_css=None,
                error="Empty CSS content"
            )
        
        # Build prompt
        prompt = self._build_prompt(css_content, design_tokens)
        
        # Call AI
        response = self.client.generate(prompt, system=self.SYSTEM_PROMPT)
        
        # Check for errors
        if "error" in response:
            return RefactoringResult(
                success=False,
                refactored_css=None,
                error=response["error"]
            )
        
        # Extract refactored CSS
        refactored = response.get("response", "").strip()
        
        if not refactored:
            return RefactoringResult(
                success=False,
                refactored_css=None,
                error="Empty response from AI"
            )
        
        # Clean up response (remove markdown if present)
        refactored = self._clean_response(refactored)
        
        # Get token count
        tokens = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)
        
        return RefactoringResult(
            success=True,
            refactored_css=refactored,
            error=None,
            tokens_used=tokens
        )
    
    def _build_prompt(self, css_content: str, design_tokens: str) -> str:
        """Build refactoring prompt"""
        return f"""Design System Tokens:
{design_tokens}

Original CSS:
{css_content}

Refactor the CSS above to use the design system tokens. Replace hardcoded values with CSS variables where they match the design tokens."""
    
    def _clean_response(self, response: str) -> str:
        """Clean up AI response, stripping any markdown code fences"""
        # Extract content from the last (or only) code fence block
        match = re.search(r'```(?:css)?\s*\n(.*?)```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # No code fences — return as-is
        return response.strip()
    
    def estimate_tokens(self, css_content: str, design_tokens: str) -> int:
        """
        Estimate token count for refactoring
        
        Args:
            css_content: CSS content
            design_tokens: Design tokens string
        
        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters
        prompt = self._build_prompt(css_content, design_tokens)
        system = self.SYSTEM_PROMPT
        
        total_chars = len(prompt) + len(system)
        return total_chars // 4
