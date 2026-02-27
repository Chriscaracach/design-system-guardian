"""
Setup verification module
Checks that all dependencies and requirements are met
"""

import sys
import subprocess
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class SetupChecker:
    """Verifies that the environment is properly set up"""
    
    def __init__(self):
        self.console = Console()
        self.issues = []
        self.warnings = []
    
    def check_all(self):
        """Run all checks and display results"""
        self.console.print("\n🎨 CSS Refactoring Tool - Setup Verification", style="bold cyan")
        self.console.print("━" * 50, style="dim")
        
        self.console.print("\n[bold]System Requirements:[/bold]")
        self.check_python()
        self.check_os()
        
        self.console.print("\n[bold]Dependencies:[/bold]")
        self.check_dependencies()
        
        self.console.print("\n[bold]AI Backend:[/bold]")
        self.check_ollama()
        self.check_model()
        
        self.console.print("\n[bold]Terminal Capabilities:[/bold]")
        self.check_terminal()
        
        self.console.print("\n[bold]File System:[/bold]")
        self.check_filesystem()
        
        self.display_summary()
    
    def check_python(self):
        """Check Python version"""
        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        
        if version_info >= (3, 10):
            self.success(f"Python {version_str} (>= 3.10 required)")
        else:
            self.error(f"Python {version_str} (3.10+ required)")
            self.issues.append("Upgrade Python to 3.10+")
    
    def check_os(self):
        """Check operating system"""
        import platform
        os_name = platform.system()
        self.success(f"Operating System: {os_name}")
    
    def check_dependencies(self):
        """Check if all dependencies are installed"""
        from importlib.metadata import version, PackageNotFoundError
        
        deps = ["rich", "requests"]
        
        for dep in deps:
            try:
                ver = version(dep)
                self.success(f"{dep} {ver}")
            except PackageNotFoundError:
                self.error(f"{dep} not installed")
                self.issues.append(f"Install {dep}")
        
        # Check for optional GIF support
        try:
            import PIL
            self.success(f"pillow {PIL.__version__} (optional - for GIF support)")
        except ImportError:
            self.warning("pillow not installed (GIF support disabled)")
        
        try:
            import term_image
            self.success("term-image (optional - for GIF support)")
        except ImportError:
            self.warning("term-image not installed (GIF support disabled)")
    
    def check_ollama(self):
        """Check if Ollama is installed and running"""
        # Check if installed
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.success("Ollama is installed")
            else:
                self.error("Ollama not found")
                self.issues.append("Install Ollama")
                return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.error("Ollama not found")
            self.issues.append("Install Ollama")
            return
        
        # Check if running
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self.success("Ollama service is running")
            else:
                self.error("Ollama service not responding")
                self.issues.append("Start Ollama")
        except Exception:
            self.error("Ollama service not running")
            self.issues.append("Start Ollama")
    
    def check_model(self):
        """Check if Llama 3.2 3B is available"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                
                # Check for llama3.2:3b or similar
                found = False
                for model in models:
                    model_name = model.get("name", "")
                    if "llama3.2" in model_name.lower() and "3b" in model_name.lower():
                        found = True
                        self.success(f"Llama 3.2 3B model available ({model_name})")
                        break
                
                if not found:
                    self.error("Llama 3.2 3B model not found")
                    self.issues.append("Pull model")
            else:
                self.warning("Could not check models (Ollama not responding)")
        except Exception:
            self.warning("Could not check models (Ollama not running)")
    
    def check_terminal(self):
        """Check terminal capabilities"""
        # Unicode
        encoding = sys.stdout.encoding.lower()
        if encoding in ['utf-8', 'utf8']:
            self.success("Unicode support")
        else:
            self.warning(f"Limited Unicode support ({encoding})")
        
        # Colors
        term = os.environ.get('TERM', '')
        colorterm = os.environ.get('COLORTERM', '')
        
        if colorterm or '256' in term:
            self.success("256 colors")
        else:
            self.warning("Limited color support")
        
        # GIF support (detect terminal)
        term_program = os.environ.get('TERM_PROGRAM', '')
        if term_program in ['iTerm.app', 'WezTerm']:
            self.success(f"GIF display supported ({term_program})")
        elif 'kitty' in term.lower():
            self.success("GIF display supported (Kitty)")
        else:
            self.warning("GIF display not supported (will use ASCII animations)")
    
    def check_filesystem(self):
        """Check file system permissions"""
        current_dir = Path.cwd()
        
        if os.access(current_dir, os.W_OK):
            self.success("Write permissions in current directory")
        else:
            self.error("No write permissions in current directory")
            self.issues.append("Run from writable directory")
        
        # Check if we can create directories
        try:
            test_dir = current_dir / ".css_tool_test"
            test_dir.mkdir(exist_ok=True)
            test_dir.rmdir()
            self.success("Can create backup directories")
        except Exception:
            self.error("Cannot create directories")
            self.issues.append("Check directory permissions")
    
    def success(self, msg):
        """Print success message"""
        self.console.print(f"  ✓ {msg}", style="green")
    
    def error(self, msg):
        """Print error message"""
        self.console.print(f"  ✗ {msg}", style="red")
    
    def warning(self, msg):
        """Print warning message"""
        self.console.print(f"  ⚠ {msg}", style="yellow")
    
    def display_summary(self):
        """Display final summary"""
        self.console.print("\n" + "━" * 50, style="dim")
        
        if not self.issues:
            self.console.print("\n✓ All checks passed! Ready to use.\n", style="bold green")
            self.console.print("Run 'python tool.py start' to begin refactoring.")
        else:
            self.console.print(f"\n✗ {len(self.issues)} issue(s) found.\n", style="bold red")
            
            # Generate installation commands
            commands = self.generate_fix_commands()
            
            if commands:
                self.console.print("Run these commands to fix:", style="bold")
                self.console.print("━" * 50, style="dim")
                for cmd in commands:
                    self.console.print(f"\n{cmd['comment']}", style="dim")
                    self.console.print(cmd['command'], style="bold cyan")
                self.console.print("\n" + "━" * 50, style="dim")
            
            self.console.print("\nAfter running these commands, verify with:")
            self.console.print("  python tool.py --check-setup", style="bold")
    
    def generate_fix_commands(self):
        """Generate copy-pastable fix commands"""
        commands = []
        
        # Check for missing dependencies
        missing_deps = [issue for issue in self.issues if "Install" in issue and "Ollama" not in issue]
        if missing_deps:
            deps = " ".join([d.split()[-1] for d in missing_deps])
            commands.append({
                'comment': "# Install missing Python dependencies",
                'command': f"pip install {deps}"
            })
        
        # Check for Ollama installation
        if any("Install Ollama" in issue for issue in self.issues):
            commands.append({
                'comment': "# Install Ollama",
                'command': "curl -fsSL https://ollama.com/install.sh | sh"
            })
        
        # Check for Ollama service
        if any("Start Ollama" in issue for issue in self.issues):
            commands.append({
                'comment': "# Start Ollama service (in a new terminal)",
                'command': "ollama serve"
            })
        
        # Check for model
        if any("Pull model" in issue for issue in self.issues):
            commands.append({
                'comment': "# Pull the AI model (~2GB download)",
                'command': "ollama pull llama3.2:3b"
            })
        
        return commands
