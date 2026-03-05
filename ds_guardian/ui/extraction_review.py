"""
Extraction Review Module
Displays the generated design-system.css for user acceptance
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich import box
import sys

try:
    import tty
    import termios
    _HAS_TTY = True
except ImportError:
    _HAS_TTY = False


class ExtractionReviewer:
    """Shows the generated design-system.css and asks for accept/reject"""

    def __init__(self, console: Console):
        self.console = console
        self.scroll_offset = 0

    def review(self, design_system_css: str, token_count: int, file_count: int) -> bool:
        """
        Display the generated design-system.css and ask the user to accept or reject.

        Args:
            design_system_css: Full content of the generated file
            token_count: Number of tokens extracted
            file_count: Number of CSS files scanned

        Returns:
            True if accepted, False if rejected
        """
        lines = design_system_css.splitlines()
        total_lines = len(lines)

        terminal_height = self.console.height
        lines_per_page = max(10, terminal_height - 17)
        max_offset = max(0, total_lines - lines_per_page)

        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="scroll_info", size=3),
            Layout(name="content", ratio=1),
            Layout(name="menu", size=5),
            Layout(name="prompt", size=2),
        )

        def _header() -> Panel:
            tbl = Table(show_header=False, box=None, expand=True)
            tbl.add_column("a", ratio=2)
            tbl.add_column("b", ratio=1)
            info = Text()
            info.append("Extracted Design System Preview", style="bold cyan")
            stats = Text()
            stats.append(f"{token_count} tokens  ", style="bold green")
            stats.append(f"from {file_count} files", style="dim white")
            tbl.add_row(info, stats)
            return Panel(tbl, border_style="cyan", box=box.ROUNDED)

        def _scroll_info() -> Panel:
            t = Text()
            t.append(
                f"Lines {self.scroll_offset + 1}–{min(self.scroll_offset + lines_per_page, total_lines)} of {total_lines}",
                style="dim cyan",
            )
            t.append("  |  ↑/k=up  ↓/j=down  g=top  G=bottom", style="dim yellow")
            return Panel(t, border_style="dim blue", box=box.SIMPLE)

        def _content() -> Panel:
            visible = lines[self.scroll_offset : self.scroll_offset + lines_per_page]
            text = Text()
            for line in visible:
                stripped = line.rstrip()
                if stripped.startswith("/*") and stripped.endswith("*/"):
                    text.append(stripped + "\n", style="bold yellow")
                elif stripped.startswith(":root"):
                    text.append(stripped + "\n", style="bold white")
                elif stripped.startswith("  --"):
                    parts = stripped.split(":", 1)
                    text.append(parts[0], style="cyan")
                    if len(parts) == 2:
                        text.append(":" + parts[1] + "\n", style="white")
                    else:
                        text.append("\n")
                elif stripped == "}":
                    text.append(stripped + "\n", style="bold white")
                else:
                    text.append(stripped + "\n", style="dim white")
            return Panel(text, title="[bold white]design-system.css[/bold white]", border_style="blue", box=box.ROUNDED)

        def _menu() -> Panel:
            menu = Text()
            menu.append("Actions: ", style="bold white")
            menu.append("[1] Accept & write files  ", style="bold green")
            menu.append("[2] Reject  ", style="bold red")
            menu.append("[q] Quit", style="bold magenta")
            return Panel(menu, border_style="yellow", box=box.ROUNDED)

        def _prompt() -> Text:
            t = Text("Navigation: ↑/k up  ↓/j down  g top  G bottom  | Choice: ", style="dim")
            return t

        def update():
            layout["header"].update(_header())
            layout["scroll_info"].update(_scroll_info())
            layout["content"].update(_content())
            layout["menu"].update(_menu())
            layout["prompt"].update(_prompt())

        with Live(layout, console=self.console, screen=True, auto_refresh=False) as live:
            while True:
                update()
                live.refresh()
                char = self._getch()

                if char in ['k', 'K', '\x1b[A']:
                    self.scroll_offset = max(0, self.scroll_offset - 1)
                elif char in ['j', 'J', '\x1b[B']:
                    self.scroll_offset = min(max_offset, self.scroll_offset + 1)
                elif char in ['u', 'U']:
                    self.scroll_offset = max(0, self.scroll_offset - lines_per_page)
                elif char in ['d', 'D']:
                    self.scroll_offset = min(max_offset, self.scroll_offset + lines_per_page)
                elif char == 'g':
                    self.scroll_offset = 0
                elif char == 'G':
                    self.scroll_offset = max_offset
                elif char == '1':
                    return True
                elif char in ['2', 'q', 'Q']:
                    return False

    def _getch(self) -> str:
        if _HAS_TTY:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                char = sys.stdin.read(1)
                if char == '\x1b':
                    n1 = sys.stdin.read(1)
                    n2 = sys.stdin.read(1)
                    return '\x1b' + n1 + n2
                return char
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        else:
            line = input("Choice (1=accept, 2=reject, j/k=scroll): ").strip()
            return line[0] if line else '2'
