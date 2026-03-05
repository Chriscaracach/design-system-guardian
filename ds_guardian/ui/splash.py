"""
Splash Screen Module
Displays welcome screen while AI processes files in background
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich import box
from rich.live import Live
import time
import threading
from pathlib import Path


class SplashScreen:
    """Displays splash screen with image and welcome text"""
    
    def __init__(self, console: Console, ascii_only: bool = False):
        """
        Initialize splash screen
        
        Args:
            console: Rich console instance
            ascii_only: If True, skip image rendering and always use ASCII art
        """
        self.console = console
        self.ascii_only = ascii_only
        self.splash_image_path = Path(__file__).parent.parent.parent / "splash.png"
        self._status_message = "Initializing"
        self._files_total = 0
        self._files_done = 0
        self._status_lock = threading.Lock()
    
    def set_status(self, message: str):
        """
        Update the status label shown on the splash screen.
        Safe to call from background threads.

        Args:
            message: Short description of what the app is currently doing
        """
        with self._status_lock:
            self._status_message = message

    def set_progress(self, done: int, total: int):
        """
        Update the file processing counters shown on the splash screen.
        Safe to call from background threads.

        Args:
            done: Number of files processed so far
            total: Total number of files to process
        """
        with self._status_lock:
            self._files_done = done
            self._files_total = total

    def show(self, duration: float = 5.0, background_task=None):
        """
        Show splash screen for specified duration
        
        Args:
            duration: How long to show splash (seconds)
            background_task: Optional function to run in background while showing splash
        
        Returns:
            Result from background_task if provided, else None
        """
        # Start background task if provided
        result = [None]
        error = [None]
        
        if background_task:
            def run_task():
                try:
                    result[0] = background_task()
                except Exception as e:
                    error[0] = e
            
            thread = threading.Thread(target=run_task, daemon=True)
            thread.start()
        
        # Create splash layout
        layout = self._create_splash_layout()
        
        # Show splash with live display
        start_time = time.time()
        with Live(layout, console=self.console, screen=True, auto_refresh=True, refresh_per_second=4) as live:
            while time.time() - start_time < duration:
                elapsed = time.time() - start_time
                remaining = duration - elapsed
                
                # Update progress indicator
                with self._status_lock:
                    current_status = self._status_message
                    files_done = self._files_done
                    files_total = self._files_total
                layout = self._create_splash_layout(remaining, duration, current_status, files_done, files_total)
                live.update(layout)
                
                # Check if background task is done
                if background_task and not thread.is_alive():
                    # Task finished early, wait a bit more for user to see splash
                    if elapsed < 2.0:
                        time.sleep(2.0 - elapsed)
                    break
                
                time.sleep(0.1)
        
        # Wait for background task to complete if still running
        if background_task and thread.is_alive():
            # Show "Still processing..." message
            self.console.print("\n[dim yellow]Still processing, please wait...[/dim yellow]")
            thread.join()
        
        # Check for errors
        if error[0]:
            self.console.clear()
            self.console.print(f"\n[red]✗ Error during initialization: {error[0]}[/red]")
            import traceback
            traceback.print_exception(type(error[0]), error[0], error[0].__traceback__)
            raise error[0]
        
        return result[0]
    
    def _create_splash_layout(
        self,
        remaining: float = None,
        duration: float = None,
        status: str = None,
        files_done: int = 0,
        files_total: int = 0,
    ) -> Layout:
        """
        Create splash screen layout
        
        Args:
            remaining: Seconds remaining (for progress indicator)
            duration: Total duration in seconds
            status: Current status label
            files_done: Number of files processed so far
            files_total: Total files to process
        
        Returns:
            Rich Layout
        """
        layout = Layout()
        
        # Try to load and display image
        image_content = self._load_image()
        
        # Build a vertical stack: image/logo + optional progress section
        grid = Table.grid(padding=(0, 0))
        grid.add_column(justify="center")

        if image_content:
            grid.add_row(Align.center(image_content))
            grid.add_row(Text(""))

        if remaining is not None and duration is not None:
            elapsed = duration - remaining

            if files_total > 0:
                # File-based progress bar
                file_progress = Progress(
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(bar_width=40, style="cyan", complete_style="bold cyan"),
                    TextColumn("[cyan]{task.completed}/{task.total}"),
                    expand=False,
                )
                file_progress.add_task("Files", total=files_total, completed=files_done)
                grid.add_row(Align.center(file_progress))

                # ETA based on per-file rate
                if files_done > 0 and files_done < files_total:
                    rate = elapsed / files_done  # seconds per file
                    eta = rate * (files_total - files_done)
                    eta_text = Text(f"ETA  ~{eta:.0f}s", style="dim cyan", justify="center")
                else:
                    eta_text = Text("", justify="center")
                grid.add_row(Align.center(eta_text))
            else:
                # Fallback time-based progress bar
                time_progress = Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(bar_width=40, style="cyan", complete_style="bold cyan"),
                    TextColumn("[cyan]{task.percentage:>3.0f}%"),
                    expand=False,
                )
                time_progress.add_task("", total=duration, completed=elapsed)
                grid.add_row(Align.center(time_progress))
                grid.add_row(Text(""))

            label = status or "Working..."
            status_text = Text(f"{label}", style="dim cyan", justify="center")
            grid.add_row(Align.center(status_text))
        
        layout.update(
            Panel(
                Align.center(grid, vertical="middle"),
                border_style="cyan",
                box=box.DOUBLE,
                padding=(2, 4)
            )
        )
        
        return layout
    
    def _load_image(self) -> Text:
        """
        Load splash image if available and convert to terminal display
        
        Returns:
            Text representation of image or ASCII art
        """
        # Try to display actual image if it exists (skip if ascii_only)
        if not self.ascii_only and self.splash_image_path.exists():
            try:
                # Try to use PIL to convert image to ASCII art
                from PIL import Image
                import os
                
                # Load and resize image
                img = Image.open(self.splash_image_path)
                
                # Calculate size for terminal (aim for ~60 chars wide)
                width = 60
                aspect_ratio = img.height / img.width
                height = int(width * aspect_ratio * 0.5)  # 0.5 because chars are taller than wide
                
                # Resize image
                img = img.resize((width, height))
                
                # Convert to grayscale
                img = img.convert('L')
                
                # ASCII characters from darkest to lightest
                ascii_chars = '@%#*+=-:. '
                
                # Convert pixels to ASCII
                ascii_art = []
                pixels = img.getdata()
                
                for i in range(0, len(pixels), width):
                    row = pixels[i:i+width]
                    ascii_row = ''.join([ascii_chars[min(pixel // 28, len(ascii_chars)-1)] for pixel in row])
                    ascii_art.append(ascii_row)
                
                # Create Text object with the ASCII art
                result = Text()
                result.append('\n'.join(ascii_art), style="cyan")
                return result
                
            except ImportError:
                # PIL not available, fall back to ASCII logo
                return self._get_ascii_logo()
            except Exception:
                # Any other error, fall back to ASCII logo
                return self._get_ascii_logo()
        else:
            return self._get_ascii_logo()
    
    def _get_ascii_logo(self) -> Text:
        """
        Get ASCII art logo
        
        Returns:
            Text with ASCII art
        """
        logo = Text()
        logo.append(r"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣶⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠤⢴⣾⣿⣿⣿⣯⠘⠳⢦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⡟⣾⣿⣿⣠⢠⣀⢻⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠒⢫⣿⣿⣿⣿⣿⣿⢸⡗⣾⣙⡷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣿⣧⢮⡯⣷⣼⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⡐⣚⣛⡛⠛⠉⢹⣽⣿⣽⠮⠓⣫⣏⠀⠀⣀⣀⣀⡀⠀⠀⠀⠀⠀
⠀⠀⢀⣴⠟⠋⠩⠉⢩⣷⣾⣿⣽⣷⣿⠤⢋⡥⠚⠳⣾⡏⠉⠉⠙⠻⢦⡀⠀⠀
⠀⢀⡿⢁⠈⢀⡠⢔⣣⠟⠿⣿⣿⣿⣗⡪⠇⠀⣢⡾⠛⣮⡢⢄⡀⠐⡈⢻⡄⠀
⢰⣾⠷⠥⠉⠑⡪⣽⠧⠀⠀⠨⡻⣟⣿⠀⣠⠞⡁⠀⠀⠚⣯⣇⡊⠉⠬⠾⣻⡆
⢨⡿⠤⣆⣒⡬⠞⣿⡑⠀⠀⠀⠀⠈⢳⣞⠁⠀⠀⠀⠀⢁⣿⠳⢥⣒⣨⠤⢿⣅
⢻⣿⣿⢋⠁⠀⢰⡇⠀⠀⠀⢠⢞⢿⣭⡍⢻⢦⡀⠀⠀⠀⢼⡇⠀⠈⠝⣿⣿⡟
⠀⣹⡏⢀⣀⣀⣸⣇⣀⣀⣀⣘⣛⣾⢶⠿⠿⣷⣽⡟⠓⢲⠶⠧⢤⣀⡠⢸⣏⠀
⢠⣿⡟⡿⡝⠀⠐⠀⠁⠈⠈⡽⠁⠀⢸⣓⣚⣿⣿⠧⣤⣄⡀⠀⠀⠈⣽⣧⣿⡀
⠘⢷⣧⣿⢷⣤⣤⣴⡶⣶⣾⣷⢤⣤⢾⠭⢭⣿⣿⣿⣶⣭⣝⡛⠶⠶⣳⣼⣿⡇
⠀⠀⠙⠛⠛⠚⠛⠛⣿⣿⣿⣿⣟⣷⡿⠓⠛⠻⠿⢿⠟⢿⠉⠛⠻⠯⠴⠶⠛⠁
⠀⠀⠀⠀⠀⠀⠀⢠⣿⣽⡯⢿⣿⡟⠷⠶⢲⡖⠶⢼⣴⣾⣔⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⡾⠁⠈⠛⠷⣾⣧⠀⠀⢸⣶⢾⠛⠉⠔⢿⣂⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣼⠍⠂⠀⢠⢣⣿⣷⠀⠄⢸⣿⡞⡄⠀⠀⡨⢷⠆⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡣⣄⡀⠀⣎⣿⣿⣿⠀⡀⢺⣿⣿⡸⡀⢀⡰⢝⡧⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠉⠓⠮⠽⣼⠛⠿⠿⠤⠤⠿⠿⠛⢷⠯⠵⠚⠋⠀⠀⠀⠀⠀⠀
|------------------|
|                  |
|   DS  GUARDIAN   |
|                  |
|------------------|
        """, style="bold cyan")
        
        return logo
