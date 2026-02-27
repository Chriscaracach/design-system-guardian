"""
CSS Refactorer Module
Handles CSS refactoring using AI
"""

from typing import Dict
from css_tool.ai.client import OllamaClient, RefactoringResult


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
    
    def refactor_batch(self, files_dict: Dict[str, str], design_tokens: str) -> Dict[str, RefactoringResult]:
        """
        Refactor multiple CSS files in a single AI request
        
        Args:
            files_dict: Dictionary mapping file paths to CSS content
            design_tokens: Design tokens context string
        
        Returns:
            Dictionary mapping file paths to RefactoringResult objects
        """
        if not files_dict:
            return {}
        
        # Build batch prompt
        prompt = self._build_batch_prompt(files_dict, design_tokens)
        
        # Call AI
        response = self.client.generate(prompt, system=self.SYSTEM_PROMPT)
        
        # Check for errors
        if "error" in response:
            # Return error for all files
            error_result = RefactoringResult(
                success=False,
                refactored_css=None,
                error=response["error"]
            )
            return {path: error_result for path in files_dict.keys()}
        
        # Extract refactored CSS
        refactored = response.get("response", "").strip()
        
        if not refactored:
            error_result = RefactoringResult(
                success=False,
                refactored_css=None,
                error="Empty response from AI"
            )
            return {path: error_result for path in files_dict.keys()}
        
        # Clean up response
        refactored = self._clean_response(refactored)
        
        # Get token count
        tokens = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)
        
        # Parse batch response back into individual files
        results = self._parse_batch_response(refactored, files_dict, tokens)
        
        return results
    
    def _build_prompt(self, css_content: str, design_tokens: str) -> str:
        """Build refactoring prompt"""
        return f"""Design System Tokens:
{design_tokens}

Original CSS:
{css_content}

Refactor the CSS above to use the design system tokens. Replace hardcoded values with CSS variables where they match the design tokens."""
    
    def _build_batch_prompt(self, files_dict: Dict[str, str], design_tokens: str) -> str:
        """Build batch refactoring prompt for multiple files"""
        files_section = ""
        for path, content in files_dict.items():
            files_section += f"\n### FILE: {path}\n{content}\n"
        
        return f"""You are refactoring multiple CSS files to use design system tokens.

Design System Tokens:
{design_tokens}

Input Files:
{files_section}

CRITICAL INSTRUCTIONS:
1. Refactor each file separately
2. Replace hardcoded values with CSS variables where they match design tokens
3. You MUST return results in this EXACT format (including the ### FILE: markers):

### FILE: buttons.css
.btn {{ background: var(--primary-blue); }}

### FILE: forms.css
.input {{ color: var(--gray-900); }}

DO NOT merge files together. DO NOT omit the ### FILE: markers. Return each file separately with its marker."""
    
    def _parse_batch_response(self, response: str, files_dict: Dict[str, str], total_tokens: int) -> Dict[str, RefactoringResult]:
        """Parse batch response back into individual file results"""
        results = {}
        tokens_per_file = total_tokens // len(files_dict) if files_dict else 0
        
        # Split response by file markers
        parts = response.split("### FILE:")
        
        for part in parts[1:]:  # Skip first empty part
            lines = part.strip().split('\n', 1)
            if len(lines) < 2:
                continue
            
            file_path = lines[0].strip()
            refactored_css = lines[1].strip()
            
            # Find matching file path (handle relative paths)
            matched_path = None
            for path in files_dict.keys():
                if file_path in path or path in file_path:
                    matched_path = path
                    break
            
            if matched_path:
                results[matched_path] = RefactoringResult(
                    success=True,
                    refactored_css=refactored_css,
                    error=None,
                    tokens_used=tokens_per_file
                )
        
        # Handle any files that weren't in the response
        for path in files_dict.keys():
            if path not in results:
                results[path] = RefactoringResult(
                    success=False,
                    refactored_css=None,
                    error="File not found in AI response"
                )
        
        return results
    
    def _clean_response(self, response: str) -> str:
        """Clean up AI response"""
        # Remove markdown code blocks
        if "```css" in response:
            response = response.split("```css")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
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
