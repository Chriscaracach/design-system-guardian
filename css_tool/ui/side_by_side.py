"""
Side-by-Side Diff Viewer
Shows original and refactored CSS in two columns with color highlighting
"""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.syntax import Syntax
from rich import box
from typing import List, Tuple
import difflib


class SideBySideDiff:
    """Creates side-by-side diff view with color highlighting"""
    
    def __init__(self):
        """Initialize side-by-side diff viewer"""
        self.console = Console()
    
    def create_lines(self, original: str, refactored: str) -> list:
        """
        Create diff as list of lines for paging
        
        Args:
            original: Original CSS content
            refactored: Refactored CSS content
        
        Returns:
            List of formatted Text objects, one per line
        """
        from rich.text import Text
        
        original_lines = original.splitlines()
        refactored_lines = refactored.splitlines()
        
        # Get line-by-line diff information
        diff_info = self._get_diff_info(original_lines, refactored_lines)
        
        # Create formatted lines
        result = []
        
        # Add header row
        header = Text()
        header.append("Original".ljust(60), style="bold white")
        header.append(" │ ", style="dim white")
        header.append("Refactored", style="bold white")
        result.append(header)
        
        # Add separator
        separator = Text()
        separator.append("─" * 60, style="dim white")
        separator.append("─┼─", style="dim white")
        separator.append("─" * 60, style="dim white")
        result.append(separator)
        
        # Add content lines
        for left, right, change_type in diff_info:
            line = Text()
            
            # Format left side (truncate and pad to 60 chars)
            if left:
                left_display = left[:60].ljust(60)
                if change_type == 'unchanged':
                    line.append(left_display, style="white")
                elif change_type in ['modified', 'removed']:
                    line.append(left_display, style="bold red")
                else:
                    line.append(left_display, style="dim white")
            else:
                line.append(" " * 60, style="dim white")
            
            # Add separator
            line.append(" │ ", style="dim white")
            
            # Format right side
            if right:
                if change_type == 'unchanged':
                    line.append(right, style="white")
                elif change_type in ['modified', 'added']:
                    line.append(right, style="bold green")
                else:
                    line.append(right, style="dim white")
            
            result.append(line)
        
        return result
    
    def create_view(self, original: str, refactored: str) -> Table:
        """
        Create side-by-side diff view showing complete files
        
        Args:
            original: Original CSS content
            refactored: Refactored CSS content
        
        Returns:
            Rich Table with side-by-side comparison
        """
        original_lines = original.splitlines()
        refactored_lines = refactored.splitlines()
        
        # Get line-by-line diff information
        diff_info = self._get_diff_info(original_lines, refactored_lines)
        
        # Create table
        table = Table(
            show_header=True,
            header_style="bold white",
            box=box.SIMPLE,
            padding=(0, 1),
            expand=True
        )
        
        table.add_column("Original", style="white", ratio=1, no_wrap=False)
        table.add_column("Refactored", style="white", ratio=1, no_wrap=False)
        
        # Add all rows with color coding
        for left, right, change_type in diff_info:
            left_text = self._format_line(left, change_type, 'left')
            right_text = self._format_line(right, change_type, 'right')
            
            table.add_row(left_text, right_text)
        
        return table
    
    def _get_diff_info(self, original_lines: List[str], refactored_lines: List[str]) -> List[Tuple[str, str, str]]:
        """
        Get line-by-line diff information
        
        Args:
            original_lines: Original CSS lines
            refactored_lines: Refactored CSS lines
        
        Returns:
            List of tuples (left_line, right_line, change_type)
            change_type: 'unchanged', 'modified', 'removed', 'added'
        """
        # Use SequenceMatcher for better alignment
        matcher = difflib.SequenceMatcher(None, original_lines, refactored_lines)
        result = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Unchanged lines
                for i in range(i1, i2):
                    result.append((original_lines[i], refactored_lines[j1 + (i - i1)], 'unchanged'))
            
            elif tag == 'replace':
                # Modified lines - show side by side
                max_len = max(i2 - i1, j2 - j1)
                for i in range(max_len):
                    left = original_lines[i1 + i] if i1 + i < i2 else ''
                    right = refactored_lines[j1 + i] if j1 + i < j2 else ''
                    result.append((left, right, 'modified'))
            
            elif tag == 'delete':
                # Removed lines - show on left only
                for i in range(i1, i2):
                    result.append((original_lines[i], '', 'removed'))
            
            elif tag == 'insert':
                # Added lines - show on right only
                for j in range(j1, j2):
                    result.append(('', refactored_lines[j], 'added'))
        
        return result
    
    def _format_line(self, line: str, change_type: str, side: str) -> Text:
        """
        Format a line with appropriate color
        
        Args:
            line: Line content
            change_type: Type of change
            side: 'left' or 'right'
        
        Returns:
            Formatted Rich Text
        """
        if not line:
            return Text("")
        
        text = Text(line)
        
        if change_type == 'unchanged':
            text.stylize("white")
        elif change_type == 'modified':
            if side == 'left':
                text.stylize("bold red")
            else:
                text.stylize("bold green")
        elif change_type == 'removed':
            text.stylize("bold red")
        elif change_type == 'added':
            text.stylize("bold green")
        
        return text


class ThreeRowLayout:
    """Three-row layout: header, side-by-side diff, bottom menu"""
    
    def __init__(self):
        """Initialize three-row layout"""
        self.console = Console()
        self.layout = Layout()
        
        # Split into three rows (header compact, diff takes most space, menu compact)
        self.layout.split_column(
            Layout(name="header", size=4),
            Layout(name="diff", ratio=1),
            Layout(name="menu", size=6)
        )
    
    def update_header(self, content):
        """Update header content"""
        self.layout["header"].update(
            Panel(content, border_style="cyan", box=box.ROUNDED)
        )
    
    def update_diff(self, content):
        """Update diff content"""
        self.layout["diff"].update(
            Panel(content, title="[bold white]Changes[/bold white]", border_style="blue", box=box.ROUNDED)
        )
    
    def update_menu(self, content):
        """Update menu content"""
        self.layout["menu"].update(
            Panel(content, border_style="yellow", box=box.ROUNDED)
        )
    
    def update_all(self, header_content, diff_content, menu_content):
        """Update all sections at once"""
        self.update_header(header_content)
        self.update_diff(diff_content)
        self.update_menu(menu_content)
    
    def render(self):
        """Render the layout"""
        return self.layout
