"""
TUI Components Module
Terminal User Interface components
"""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich import box
from typing import List, Optional, Callable
import time


class TwoColumnLayout:
    """Two-column TUI layout manager with 60/40 split"""
    
    def __init__(self):
        """Initialize layout"""
        self.console = Console()
        self.layout = Layout()
        
        # Split into two columns (60% left, 40% right)
        self.layout.split_row(
            Layout(name="left", ratio=3),
            Layout(name="right", ratio=2)
        )
    
    def update_left(self, content):
        """Update left column content"""
        self.layout["left"].update(
            Panel(content, border_style="blue", box=box.ROUNDED)
        )
    
    def update_right(self, content):
        """Update right column content"""
        self.layout["right"].update(
            Panel(content, border_style="cyan", box=box.ROUNDED)
        )
    
    def update_both(self, left_content, right_content):
        """Update both columns at once"""
        self.update_left(left_content)
        self.update_right(right_content)
    
    def render(self):
        """Render the layout"""
        return self.layout


class WorkingAnimation:
    """Working/loading animation for right column"""
    
    ANIMATIONS = {
        'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        'line': ['|', '/', '-', '\\'],
        'arrow': ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'],
        'box': ['◰', '◳', '◲', '◱'],
        'dots2': ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'],
    }
    
    def __init__(self, style: str = 'dots'):
        """
        Initialize animation
        
        Args:
            style: Animation style (dots, line, arrow, box, dots2)
        """
        self.frames = self.ANIMATIONS.get(style, self.ANIMATIONS['dots'])
        self.current_frame = 0
    
    def next_frame(self) -> str:
        """Get next animation frame"""
        frame = self.frames[self.current_frame]
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        return frame
    
    def create_panel(self, message: str = "Working...") -> Panel:
        """Create animated panel"""
        frame = self.next_frame()
        text = Text()
        text.append(f"\n{frame} ", style="bold cyan")
        text.append(message, style="white")
        text.append("\n")
        
        return Panel(
            text,
            title="Status",
            border_style="cyan",
            box=box.ROUNDED
        )


class ButtonMenu:
    """Interactive button menu with arrow key navigation"""
    
    def __init__(self, options: List[str], selected: int = 0):
        """
        Initialize button menu
        
        Args:
            options: List of button labels
            selected: Initially selected button index
        """
        self.options = options
        self.selected = selected
    
    def move_up(self):
        """Move selection up"""
        self.selected = (self.selected - 1) % len(self.options)
    
    def move_down(self):
        """Move selection down"""
        self.selected = (self.selected + 1) % len(self.options)
    
    def get_selected(self) -> str:
        """Get currently selected option"""
        return self.options[self.selected]
    
    def render(self) -> Panel:
        """Render button menu"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Button", justify="left")
        
        for i, option in enumerate(self.options):
            if i == self.selected:
                # Selected button
                table.add_row(f"→ [{option}]", style="bold cyan on black")
            else:
                # Unselected button
                table.add_row(f"  [{option}]", style="dim white")
        
        return Panel(
            table,
            title="Actions",
            border_style="cyan",
            box=box.ROUNDED
        )


class DiffViewer:
    """Displays CSS diff in left column"""
    
    def __init__(self, diff_lines: List[str], filename: str):
        """
        Initialize diff viewer
        
        Args:
            diff_lines: List of formatted diff lines
            filename: Name of file being reviewed
        """
        self.diff_lines = diff_lines
        self.filename = filename
        self.scroll_offset = 0
        self.visible_lines = 30
    
    def scroll_up(self, amount: int = 1):
        """Scroll up"""
        self.scroll_offset = max(0, self.scroll_offset - amount)
    
    def scroll_down(self, amount: int = 1):
        """Scroll down"""
        max_offset = max(0, len(self.diff_lines) - self.visible_lines)
        self.scroll_offset = min(max_offset, self.scroll_offset + amount)
    
    def render(self) -> Panel:
        """Render diff viewer"""
        # Get visible lines
        visible = self.diff_lines[self.scroll_offset:self.scroll_offset + self.visible_lines]
        
        # Create text with syntax highlighting
        text = Text()
        for line in visible:
            if line.strip().startswith('+'):
                text.append(line + '\n', style="green")
            elif line.strip().startswith('-'):
                text.append(line + '\n', style="red")
            else:
                text.append(line + '\n', style="dim white")
        
        # Add scroll indicator
        if len(self.diff_lines) > self.visible_lines:
            total = len(self.diff_lines)
            current = self.scroll_offset + self.visible_lines
            scroll_info = f"[{current}/{total} lines]"
            title = f"{self.filename} {scroll_info}"
        else:
            title = self.filename
        
        return Panel(
            text,
            title=title,
            border_style="blue",
            box=box.ROUNDED
        )


class StatusDisplay:
    """Status display for right column"""
    
    def __init__(self):
        """Initialize status display"""
        self.current_file = 0
        self.total_files = 0
        self.status = "Ready"
        self.stats = {}
    
    def update(self, current: int, total: int, status: str, stats: dict = None):
        """Update status"""
        self.current_file = current
        self.total_files = total
        self.status = status
        if stats:
            self.stats = stats
    
    def render(self) -> Panel:
        """Render status display"""
        text = Text()
        
        # Progress
        text.append(f"File {self.current_file} of {self.total_files}\n\n", style="bold white")
        
        # Status
        text.append(f"Status: ", style="dim white")
        text.append(f"{self.status}\n\n", style="cyan")
        
        # Stats
        if self.stats:
            if 'added' in self.stats:
                text.append(f"+ {self.stats['added']} lines added\n", style="green")
            if 'removed' in self.stats:
                text.append(f"- {self.stats['removed']} lines removed\n", style="red")
            if 'tokens' in self.stats:
                text.append(f"\n{self.stats['tokens']} tokens used", style="dim white")
        
        return Panel(
            text,
            title="Progress",
            border_style="cyan",
            box=box.ROUNDED
        )


class SummaryDisplay:
    """Summary display after processing"""
    
    def __init__(self, total_files: int, accepted: int, rejected: int, skipped: int):
        """Initialize summary"""
        self.total_files = total_files
        self.accepted = accepted
        self.rejected = rejected
        self.skipped = skipped
    
    def render(self) -> Panel:
        """Render summary"""
        table = Table(show_header=False, box=None)
        table.add_column("Label", style="dim white")
        table.add_column("Value", style="bold white")
        
        table.add_row("Total files", str(self.total_files))
        table.add_row("Accepted", f"[green]{self.accepted}[/green]")
        table.add_row("Rejected", f"[red]{self.rejected}[/red]")
        table.add_row("Skipped", f"[yellow]{self.skipped}[/yellow]")
        
        return Panel(
            table,
            title="✓ Complete",
            border_style="green",
            box=box.ROUNDED
        )


def show_spinner(message: str, duration: float = 2.0):
    """Show a spinner for a duration"""
    console = Console()
    
    with console.status(f"[cyan]{message}...", spinner="dots") as status:
        time.sleep(duration)


def show_progress_bar(items: List, process_fn: Callable, description: str = "Processing"):
    """Show progress bar while processing items"""
    console = Console()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task(description, total=len(items))
        
        results = []
        for item in items:
            result = process_fn(item)
            results.append(result)
            progress.advance(task)
        
        return results
