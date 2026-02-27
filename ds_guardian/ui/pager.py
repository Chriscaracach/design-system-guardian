"""
Interactive Pager Module
Keyboard-based navigation for viewing large diffs
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich import box
import sys
import tty
import termios


class InteractivePager:
    """Interactive pager with keyboard navigation and multi-panel support"""
    
    def __init__(self, console: Console, rules_file: str = None):
        """
        Initialize pager
        
        Args:
            console: Rich console instance
            rules_file: Path to rules.md file to display in third column
        """
        self.console = console
        self.scroll_offset = 0
        self.rules_scroll_offset = 0
        self.active_panel = 'diff'  # 'diff' or 'rules'
        self.rules_content = []
        
        # Load rules content if provided
        if rules_file:
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    self.rules_content = f.read().splitlines()
            except Exception:
                self.rules_content = ["Rules file not found"]
    
    def show(self, content_lines: list, header: Table, menu: Text, lines_per_page: int = None) -> str:
        """
        Show content with keyboard navigation using Live display
        
        Args:
            content_lines: List of content lines to display
            header: Header content
            menu: Menu content
            lines_per_page: Lines to show per page (auto-detect if None)
        
        Returns:
            User's choice (1-5)
        """
        from rich.layout import Layout
        
        # Auto-detect terminal height
        if lines_per_page is None:
            terminal_height = self.console.height
            # Reserve space for header (4) + menu (6) + borders (4) + scroll info (3)
            lines_per_page = max(10, terminal_height - 17)
        
        total_lines = len(content_lines)
        max_offset = max(0, total_lines - lines_per_page)
        
        total_rules_lines = len(self.rules_content)
        max_rules_offset = max(0, total_rules_lines - lines_per_page)
        
        # Create layout with three columns if rules are available
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="scroll_info", size=3),
            Layout(name="content", ratio=1),
            Layout(name="menu", size=6),
            Layout(name="prompt", size=2)
        )
        
        # Split content into two columns if rules are available
        if self.rules_content:
            layout["content"].split_row(
                Layout(name="diff", ratio=2),
                Layout(name="rules", ratio=1)
            )
        
        def update_display():
            """Update the display with current scroll position"""
            # Header
            layout["header"].update(Panel(header, border_style="cyan", box=box.ROUNDED))
            
            # Scroll info
            scroll_info = Text()
            if self.rules_content:
                # Show which panel is active
                if self.active_panel == 'diff':
                    scroll_info.append("[DIFF ACTIVE] ", style="bold green")
                    scroll_info.append(f"Lines {self.scroll_offset + 1}-{min(self.scroll_offset + lines_per_page, total_lines)} of {total_lines}", style="dim cyan")
                else:
                    scroll_info.append("[RULES ACTIVE] ", style="bold green")
                    scroll_info.append(f"Lines {self.rules_scroll_offset + 1}-{min(self.rules_scroll_offset + lines_per_page, total_rules_lines)} of {total_rules_lines}", style="dim cyan")
                scroll_info.append(" | ", style="dim white")
                scroll_info.append("TAB=switch ↑/k=up ↓/j=down", style="dim yellow")
            else:
                if total_lines > lines_per_page:
                    scroll_info.append(f"Lines {self.scroll_offset + 1}-{min(self.scroll_offset + lines_per_page, total_lines)} of {total_lines}", style="dim cyan")
                    scroll_info.append(" | ", style="dim white")
                    scroll_info.append("↑/k=up ↓/j=down", style="dim yellow")
            
            if scroll_info.plain:
                layout["scroll_info"].update(Panel(scroll_info, border_style="dim blue", box=box.SIMPLE))
            else:
                layout["scroll_info"].update("")
            
            # Content - diff panel
            visible_lines = content_lines[self.scroll_offset:self.scroll_offset + lines_per_page]
            from rich.console import Group
            content_group = Group(*visible_lines)
            
            if self.rules_content:
                # Diff panel (left/center)
                diff_border = "bold blue" if self.active_panel == 'diff' else "dim blue"
                layout["content"]["diff"].update(
                    Panel(
                        content_group,
                        title="[bold white]Changes[/bold white]" if self.active_panel == 'diff' else "[dim]Changes[/dim]",
                        border_style=diff_border,
                        box=box.ROUNDED
                    )
                )
                
                # Rules panel (right)
                visible_rules = self.rules_content[self.rules_scroll_offset:self.rules_scroll_offset + lines_per_page]
                rules_text = Text("\n".join(visible_rules))
                rules_border = "bold yellow" if self.active_panel == 'rules' else "dim yellow"
                layout["content"]["rules"].update(
                    Panel(
                        rules_text,
                        title="[bold white]Rules (rules.md)[/bold white]" if self.active_panel == 'rules' else "[dim]Rules (rules.md)[/dim]",
                        border_style=rules_border,
                        box=box.ROUNDED
                    )
                )
            else:
                # Single panel mode
                layout["content"].update(
                    Panel(
                        content_group,
                        title="[bold white]Changes[/bold white]",
                        border_style="blue",
                        box=box.ROUNDED
                    )
                )
            
            # Menu
            layout["menu"].update(Panel(menu, border_style="yellow", box=box.ROUNDED))
            
            # Prompt
            prompt_text = Text("Navigation: ", style="dim")
            if self.rules_content:
                prompt_text.append("TAB=switch panel ", style="dim yellow")
            prompt_text.append("↑/k=up ↓/j=down | Choice: ", style="dim")
            layout["prompt"].update(prompt_text)
        
        # Use Live display to prevent flashing
        with Live(layout, console=self.console, screen=True, auto_refresh=False) as live:
            while True:
                update_display()
                live.refresh()
                
                # Read single character
                char = self._getch()
                
                # Handle panel switching
                if char == '\t':  # TAB key
                    if self.rules_content:
                        self.active_panel = 'rules' if self.active_panel == 'diff' else 'diff'
                    continue
                
                # Handle navigation based on active panel
                if self.active_panel == 'diff':
                    if char in ['k', 'K', '\x1b[A']:  # k or up arrow
                        self.scroll_offset = max(0, self.scroll_offset - 1)
                    elif char in ['j', 'J', '\x1b[B']:  # j or down arrow
                        self.scroll_offset = min(max_offset, self.scroll_offset + 1)
                    elif char in ['u', 'U']:  # page up
                        self.scroll_offset = max(0, self.scroll_offset - lines_per_page)
                    elif char in ['d', 'D']:  # page down
                        self.scroll_offset = min(max_offset, self.scroll_offset + lines_per_page)
                    elif char in ['g']:  # go to top
                        self.scroll_offset = 0
                    elif char in ['G']:  # go to bottom
                        self.scroll_offset = max_offset
                else:  # rules panel active
                    if char in ['k', 'K', '\x1b[A']:  # k or up arrow
                        self.rules_scroll_offset = max(0, self.rules_scroll_offset - 1)
                    elif char in ['j', 'J', '\x1b[B']:  # j or down arrow
                        self.rules_scroll_offset = min(max_rules_offset, self.rules_scroll_offset + 1)
                    elif char in ['u', 'U']:  # page up
                        self.rules_scroll_offset = max(0, self.rules_scroll_offset - lines_per_page)
                    elif char in ['d', 'D']:  # page down
                        self.rules_scroll_offset = min(max_rules_offset, self.rules_scroll_offset + lines_per_page)
                    elif char in ['g']:  # go to top
                        self.rules_scroll_offset = 0
                    elif char in ['G']:  # go to bottom
                        self.rules_scroll_offset = max_rules_offset
                
                # Handle choices (work regardless of active panel)
                if char in ['1', '2', '3', '4', '5']:
                    # User made a choice
                    return char
                elif char in ['q', 'Q']:
                    return '5'  # Quit
    
    def _getch(self):
        """Get a single character from stdin"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            char = sys.stdin.read(1)
            
            # Handle arrow keys (escape sequences)
            if char == '\x1b':
                next1 = sys.stdin.read(1)
                next2 = sys.stdin.read(1)
                return '\x1b' + next1 + next2
            
            return char
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
