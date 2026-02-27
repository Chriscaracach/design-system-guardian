"""
Diff Generator Module
Creates visual diffs between original and refactored CSS
"""

import difflib
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum


class DiffType(Enum):
    """Type of diff line"""
    UNCHANGED = 'unchanged'
    ADDED = 'added'
    REMOVED = 'removed'
    CONTEXT = 'context'


@dataclass
class DiffLine:
    """Represents a single line in a diff"""
    line_num_old: int | None
    line_num_new: int | None
    content: str
    diff_type: DiffType
    
    def __str__(self):
        if self.diff_type == DiffType.ADDED:
            return f"+ {self.content}"
        elif self.diff_type == DiffType.REMOVED:
            return f"- {self.content}"
        else:
            return f"  {self.content}"


class DiffGenerator:
    """Generates diffs between original and refactored CSS"""
    
    def __init__(self, context_lines: int = 3):
        """
        Initialize diff generator
        
        Args:
            context_lines: Number of context lines to show around changes
        """
        self.context_lines = context_lines
    
    def generate(self, original: str, refactored: str) -> List[DiffLine]:
        """
        Generate diff between original and refactored CSS
        
        Args:
            original: Original CSS content
            refactored: Refactored CSS content
        
        Returns:
            List of DiffLine objects
        """
        original_lines = original.splitlines()
        refactored_lines = refactored.splitlines()
        
        # Use difflib to get the diff
        differ = difflib.Differ()
        diff = list(differ.compare(original_lines, refactored_lines))
        
        # Convert to DiffLine objects
        diff_lines = []
        old_line_num = 1
        new_line_num = 1
        
        for line in diff:
            if len(line) < 2:
                continue
            
            marker = line[0]
            content = line[2:]
            
            if marker == ' ':
                # Unchanged line
                diff_lines.append(DiffLine(
                    line_num_old=old_line_num,
                    line_num_new=new_line_num,
                    content=content,
                    diff_type=DiffType.UNCHANGED
                ))
                old_line_num += 1
                new_line_num += 1
            elif marker == '-':
                # Removed line
                diff_lines.append(DiffLine(
                    line_num_old=old_line_num,
                    line_num_new=None,
                    content=content,
                    diff_type=DiffType.REMOVED
                ))
                old_line_num += 1
            elif marker == '+':
                # Added line
                diff_lines.append(DiffLine(
                    line_num_old=None,
                    line_num_new=new_line_num,
                    content=content,
                    diff_type=DiffType.ADDED
                ))
                new_line_num += 1
            elif marker == '?':
                # Skip hint lines
                continue
        
        return diff_lines
    
    def generate_unified(self, original: str, refactored: str, filename: str = "file.css") -> str:
        """
        Generate unified diff format
        
        Args:
            original: Original CSS content
            refactored: Refactored CSS content
            filename: Filename for diff header
        
        Returns:
            Unified diff string
        """
        original_lines = original.splitlines(keepends=True)
        refactored_lines = refactored.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            refactored_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm='\n'
        )
        
        return ''.join(diff)
    
    def get_stats(self, diff_lines: List[DiffLine]) -> dict:
        """
        Get statistics about the diff
        
        Args:
            diff_lines: List of DiffLine objects
        
        Returns:
            Dictionary with stats
        """
        added = sum(1 for line in diff_lines if line.diff_type == DiffType.ADDED)
        removed = sum(1 for line in diff_lines if line.diff_type == DiffType.REMOVED)
        unchanged = sum(1 for line in diff_lines if line.diff_type == DiffType.UNCHANGED)
        
        return {
            'added': added,
            'removed': removed,
            'unchanged': unchanged,
            'total': len(diff_lines),
            'has_changes': added > 0 or removed > 0
        }
    
    def format_for_display(self, diff_lines: List[DiffLine], max_width: int = 80) -> List[str]:
        """
        Format diff lines for terminal display
        
        Args:
            diff_lines: List of DiffLine objects
            max_width: Maximum width for lines
        
        Returns:
            List of formatted strings
        """
        formatted = []
        
        for line in diff_lines:
            # Truncate long lines
            content = line.content
            if len(content) > max_width - 10:
                content = content[:max_width - 13] + "..."
            
            # Format with line numbers
            if line.diff_type == DiffType.ADDED:
                old_num = "    "
                new_num = f"{line.line_num_new:4d}" if line.line_num_new else "    "
                formatted.append(f"{old_num} {new_num} + {content}")
            elif line.diff_type == DiffType.REMOVED:
                old_num = f"{line.line_num_old:4d}" if line.line_num_old else "    "
                new_num = "    "
                formatted.append(f"{old_num} {new_num} - {content}")
            else:
                old_num = f"{line.line_num_old:4d}" if line.line_num_old else "    "
                new_num = f"{line.line_num_new:4d}" if line.line_num_new else "    "
                formatted.append(f"{old_num} {new_num}   {content}")
        
        return formatted
