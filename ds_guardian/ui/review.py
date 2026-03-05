"""
Interactive Review Module
Handles the interactive review experience
"""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich import box
from typing import List
from pathlib import Path
import os

from ds_guardian.ui.components import DiffViewer, ButtonMenu, StatusDisplay
from ds_guardian.ui.diff import DiffGenerator
from ds_guardian.core.session import FileChange
from ds_guardian.ui.side_by_side import SideBySideDiff, ThreeRowLayout
from ds_guardian.ui.pager import InteractivePager


class InteractiveReviewer:
    """Manages interactive review with side-by-side diff view"""
    
    def __init__(self, changes: List[FileChange], diff_generator: DiffGenerator, rules_file: str = 'design_system.css'):
        """
        Initialize interactive reviewer
        
        Args:
            changes: List of file changes to review
            diff_generator: Diff generator instance
            rules_file: Path to design_system.css file to display
        """
        self.changes = changes
        self.diff_generator = diff_generator
        self.console = Console()
        self.current_index = 0
        self.decisions = {}  # file_index -> 'accepted'/'rejected'/'skipped'
        self.diff_viewer = SideBySideDiff()
        self.pager = InteractivePager(self.console, rules_file=rules_file)
    
    def review_all(self) -> dict:
        """
        Review all changes interactively
        
        Returns:
            Dictionary mapping file indices to decisions
        """
        if not self.changes:
            return {}
        
        # Show summary first
        self._show_summary()
        
        # Review each file
        for i, change in enumerate(self.changes):
            self.current_index = i
            decision = self._review_file(change, i)
            self.decisions[i] = decision
            
            # Check for early exit
            if decision == 'quit':
                break
            elif decision == 'accept_all':
                # Accept all remaining files
                for j in range(i, len(self.changes)):
                    self.decisions[j] = 'accepted'
                break
        
        return self.decisions
    
    def _show_summary(self):
        """Show summary before review"""
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold cyan]📋 Review Changes[/bold cyan]")
        self.console.print("=" * 60)
        
        total_added = sum(c.lines_added for c in self.changes)
        total_removed = sum(c.lines_removed for c in self.changes)
        total_tokens = sum(c.tokens_used for c in self.changes)
        
        self.console.print(f"\nTotal files with changes: {len(self.changes)}")
        self.console.print(f"Total lines added: [green]+{total_added}[/green]")
        self.console.print(f"Total lines removed: [red]-{total_removed}[/red]")
        self.console.print(f"Total tokens used: {total_tokens}")
        self.console.print()
    
    def _review_file(self, change: FileChange, index: int) -> str:
        """
        Review a single file
        
        Args:
            change: File change to review
            index: Current file index
        
        Returns:
            Decision: 'accepted', 'rejected', 'skipped', 'accept_all', or 'quit'
        """
        # Header: File info and stats
        header_content = self._create_header_content(change, index)
        
        # Diff: Side-by-side comparison as lines
        diff_lines = self.diff_viewer.create_lines(change.original_css, change.refactored_css)
        
        # Menu: Action buttons
        menu_content = self._create_menu_content()
        
        # Use interactive pager for navigation
        choice = self.pager.show(diff_lines, header_content, menu_content)
        
        # Map choice to decision
        return self._map_choice(choice)
    
    def _create_header_content(self, change: FileChange, index: int) -> Table:
        """Create header content with file info and stats"""
        table = Table(show_header=False, box=None, expand=True)
        table.add_column("Info", style="white", ratio=2)
        table.add_column("Stats", style="white", ratio=1)
        
        # File info
        file_info = Text()
        file_info.append(f"File {index + 1}/{len(self.changes)}: ", style="bold white")
        file_info.append(f"{change.relative_path}", style="bold cyan")
        
        # Stats
        stats = Text()
        stats.append(f"[green]+{change.lines_added}[/green] ", style="green")
        stats.append(f"[red]-{change.lines_removed}[/red] ", style="red")
        stats.append(f"| {change.tokens_used} tokens", style="dim white")
        
        table.add_row(file_info, stats)
        return table
    
    def _create_menu_content(self) -> Text:
        """Create menu content with action buttons"""
        menu = Text()
        menu.append("Actions: ", style="bold white")
        menu.append("[1] Accept  ", style="bold green")
        menu.append("[2] Reject  ", style="bold red")
        menu.append("[3] Skip  ", style="bold yellow")
        menu.append("[4] Accept All  ", style="bold cyan")
        menu.append("[5/q] Quit", style="bold magenta")
        return menu
    
    def _map_choice(self, choice: str) -> str:
        """Map numeric choice to decision"""
        mapping = {
            '1': 'accepted',
            '2': 'rejected',
            '3': 'skipped',
            '4': 'accept_all',
            '5': 'quit'
        }
        decision = mapping.get(choice, 'skipped')
        
        # Print feedback
        feedback = {
            'accepted': '[green]✓ Accepted[/green]',
            'rejected': '[red]✗ Rejected[/red]',
            'skipped': '[yellow]⊘ Skipped[/yellow]',
            'accept_all': '[green]✓ Accepted all remaining files[/green]',
            'quit': '[yellow]Saving and quitting...[/yellow]'
        }
        
        if decision in feedback:
            self.console.print(feedback[decision])
        
        return decision
