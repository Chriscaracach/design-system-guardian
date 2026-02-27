"""
Splash Screen Module
Displays welcome screen while AI processes files in background
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich import box
from rich.live import Live
import time
import threading
from pathlib import Path


class SplashScreen:
    """Displays splash screen with image and welcome text"""
    
    def __init__(self, console: Console):
        """
        Initialize splash screen
        
        Args:
            console: Rich console instance
        """
        self.console = console
        self.splash_image_path = Path(__file__).parent.parent.parent / "splash.png"
    
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
                layout = self._create_splash_layout(remaining)
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
    
    def _create_splash_layout(self, remaining: float = None) -> Layout:
        """
        Create splash screen layout
        
        Args:
            remaining: Seconds remaining (for progress indicator)
        
        Returns:
            Rich Layout
        """
        layout = Layout()
        
        # Try to load and display image
        image_content = self._load_image()
        
        # Create welcome text
        welcome_text = Text()
        welcome_text.append("\n")
        welcome_text.append("CSS Design Token Refactoring Tool", style="bold cyan")
        welcome_text.append("\n\n")
        welcome_text.append("Automatically refactor your CSS to use design tokens", style="white")
        welcome_text.append("\n")
        welcome_text.append("from your design system rules", style="white")
        welcome_text.append("\n\n")
        
        if remaining is not None:
            dots = "." * (int(time.time() * 2) % 4)
            welcome_text.append(f"Processing with AI{dots}", style="dim yellow")
        
        # Combine image and text
        content = Text()
        if image_content:
            content.append(image_content)
            content.append("\n\n")
        content.append(welcome_text)
        
        # Center everything
        centered = Align.center(content, vertical="middle")
        
        layout.update(
            Panel(
                centered,
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
        # Try to display actual image if it exists
        if self.splash_image_path.exists():
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
        logo.append("""
   ╔═══════════════════════════════════════╗
   ║                                       ║
   ║     CSS DESIGN TOKEN REFACTORING      ║
   ║                                       ║
   ║          ╭─────────────────╮          ║
   ║          │   .css  →  var  │          ║
   ║          ╰─────────────────╯          ║
   ║                                       ║
   ╚═══════════════════════════════════════╝
        """, style="bold cyan")
        
        return logo
