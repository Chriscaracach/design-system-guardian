"""
Main Refactoring Workflow
Orchestrates the entire refactoring process
"""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ds_guardian.core.scanner import FileScanner, format_size
from ds_guardian.core.rules import RulesParser
from ds_guardian.core.session import RefactoringSession, FileChange
from ds_guardian.core.writer import FileWriter
from ds_guardian.ai.client import OllamaClient
from ds_guardian.ai.anthropic_client import AnthropicClient
from ds_guardian.ai.openai_client import OpenAIClient
from ds_guardian.ai.gemini_client import GeminiClient
from ds_guardian.ai.config import ModelConfig
from ds_guardian.ai.refactorer import CSSRefactorer
from ds_guardian.ai.optimizer import PromptOptimizer
from ds_guardian.ui.diff import DiffGenerator
from ds_guardian.ui.review import InteractiveReviewer
from ds_guardian.ui.splash import SplashScreen


class RefactoringWorkflow:
    """Manages a complete refactoring workflow"""
    
    def __init__(self, target_dir: str, rules_file: str, dry_run: bool = False, auto_apply: bool = False, max_workers: int = 3, model_config: ModelConfig = None, ascii_only: bool = False):
        """
        Initialize refactoring workflow
        
        Args:
            target_dir: Directory to scan
            rules_file: Path to design_system.css
            dry_run: Preview only, don't write files
            auto_apply: Apply all changes without review
            max_workers: Number of parallel workers for AI processing (default: 3)
            model_config: Persisted AI provider configuration (loads from disk if None)
            ascii_only: Disable image/GIF rendering, use ASCII art only
        """
        self.target_dir = Path(target_dir)
        # Resolve rules_file relative to target_dir when it is a bare filename
        rules_path = Path(rules_file)
        if not rules_path.is_absolute() and rules_path.parent == Path('.'):
            self.rules_file = str(self.target_dir / rules_path.name)
        else:
            self.rules_file = str(rules_path)
        self.dry_run = dry_run
        self.auto_apply = auto_apply
        self.max_workers = max_workers
        self.model_config = model_config or ModelConfig.load()
        self.ascii_only = ascii_only
        
        self.console = Console()
        self.scanner = FileScanner(target_dir)
        self.diff_generator = DiffGenerator()
        self.writer = FileWriter(target_dir=self.target_dir)
        self.session = RefactoringSession(target_dir=self.target_dir)
        self.optimizer = PromptOptimizer()
        
        self.files = []
        self.rules = None
        self.client = None
        self.refactorer = None
        self._bg_error = None
    
    def run(self):
        """Run the complete refactoring workflow"""
        try:
            # Check for existing session and offer to resume
            if self.session.exists():
                self.console.print("[yellow]⚠ A saved session was found.[/yellow]")
                if Confirm.ask("Resume previous session instead of starting fresh?", default=True):
                    return self.resume()
                else:
                    self.session.clear()
                    self.session = RefactoringSession(target_dir=self.target_dir)

            # Show splash screen while processing in background
            splash = SplashScreen(self.console, ascii_only=self.ascii_only)
            
            def background_processing():
                """Run initialization and processing in background"""
                try:
                    splash.set_status("Scanning CSS files...")
                    if not self._scan_files():
                        return False
                    
                    splash.set_status("Loading design tokens...")
                    if not self._load_rules():
                        return False
                    
                    splash.set_status("Connecting to AI model...")
                    if not self._initialize_ai():
                        return False
                    
                    splash.set_status("Processing files...")
                    splash.set_progress(0, len(self.files))
                    result = self._process_all_files(splash)
                    if result == 'no_changes':
                        return 'no_changes'
                    
                    splash.set_status(f"Done — {len(self.session.changes)} files with changes")
                    return True
                except Exception as e:
                    self._bg_error = str(e)
                    return False
            
            # Show splash while processing (up to 60 seconds)
            success = splash.show(duration=60.0, background_task=background_processing)
            
            # Clear screen after splash
            self.console.clear()
            
            if success == 'no_changes':
                self.console.print("[yellow]No refactorable values found — the CSS may already use design tokens, or no token values matched.[/yellow]")
                return True
            
            if not success:
                if self._bg_error:
                    self.console.print(f"[red]✗ {self._bg_error}[/red]")
                else:
                    self.console.print("[red]✗ Initialization failed. Run 'dsg --check-setup' to diagnose.[/red]")
                return False
            
            # Show what was processed
            self.console.print(f"[green]✓ Found {len(self.files)} CSS files[/green]")
            self.console.print(f"[green]✓ Loaded {self.rules.get_token_count()} design tokens[/green]")
            self.console.print(f"[green]✓ Processed {len(self.session.changes)} files with changes[/green]\n")
            
            # Save session
            self.session.metadata['rules_file'] = self.rules_file
            self.session.metadata['target_dir'] = str(self.target_dir)
            self.session.save()
            
            # Phase 2: Review and apply changes
            if self.auto_apply:
                self._auto_apply_all()
            else:
                self._review_changes()
            
            return True
            
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]✗ Interrupted by user[/yellow]")
            # Save session before exiting
            self.session.save()
            self.console.print(f"[yellow]Session saved. Resume with: dsg review[/yellow]")
            return False
        except Exception as e:
            self.console.print(f"\n[red]✗ Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            return False
    
    def _scan_files(self) -> bool:
        """Scan for CSS files (silent for background processing)"""
        try:
            self.files = self.scanner.scan()
        except Exception as e:
            self._bg_error = f"Failed to scan directory: {e}"
            return False
        
        if not self.files:
            self._bg_error = f"No CSS/SCSS/LESS files found in: {self.target_dir}"
            return False
        
        return True
    
    def _load_rules(self) -> bool:
        """Load design system rules (silent for background processing)"""
        try:
            parser = RulesParser(self.rules_file)
            self.rules = parser.parse()
        except FileNotFoundError:
            self._bg_error = f"Design system file not found: '{self.rules_file}' — create design_system.css with 'dsg extract', or pass --rules <path>."
            return False
        except Exception as e:
            self._bg_error = f"Failed to load rules: {e}"
            return False
        
        if self.rules.get_token_count() == 0:
            self._bg_error = f"No design tokens found in '{self.rules_file}'. Check that it has /* Category */ sections with --token: value; declarations."
            return False
        
        return True
    
    def _initialize_ai(self) -> bool:
        """Initialize AI client and refactorer (runs silently in background)"""
        try:
            cfg = self.model_config
            api_key = cfg.resolved_api_key()

            if cfg.provider == 'anthropic':
                self.client = AnthropicClient(api_key=api_key, model=cfg.model)
                unavailable_msg = (
                    "Anthropic client unavailable. Check that the 'anthropic' package is installed "
                    "(pip install anthropic) and that ANTHROPIC_API_KEY is set."
                )
            elif cfg.provider == 'openai':
                self.client = OpenAIClient(api_key=api_key, model=cfg.model)
                unavailable_msg = (
                    "OpenAI client unavailable. Check that the 'openai' package is installed "
                    "(pip install openai) and that OPENAI_API_KEY is set."
                )
            elif cfg.provider == 'gemini':
                self.client = GeminiClient(api_key=api_key, model=cfg.model)
                unavailable_msg = (
                    "Gemini client unavailable. Check that the 'google-generativeai' package is installed "
                    "(pip install google-generativeai) and that GEMINI_API_KEY is set."
                )
            else:
                self.client = OllamaClient(model=cfg.model)
                unavailable_msg = "Could not connect to Ollama. Is it running? Try: ollama serve"

            if not self.client.is_available():
                self._bg_error = unavailable_msg
                return False

            self.refactorer = CSSRefactorer(self.client)
            return True

        except Exception as e:
            self._bg_error = f"AI initialization error: {e}"
            return False
    
    
    def _process_all_files(self, splash=None):
        """Process all files in parallel using ThreadPoolExecutor"""
        all_css_content = ""
        for file in self.files:
            with open(file.path, 'r', encoding='utf-8') as f:
                all_css_content += f.read() + "\n"

        filtered_rules = self.optimizer.filter_relevant_tokens(all_css_content, self.rules)
        design_tokens = RulesParser(self.rules_file).generate_prompt_context(filtered_rules)

        session_lock = threading.Lock()
        completed_count = [0]

        def process_file(file):
            with open(file.path, 'r', encoding='utf-8') as f:
                original_css = f.read()

            result = self.refactorer.refactor(original_css, design_tokens)
            if not result.success:
                return None

            diff_lines = self.diff_generator.generate(original_css, result.refactored_css)
            diff_stats = self.diff_generator.get_stats(diff_lines)
            if not diff_stats['has_changes']:
                return None

            return FileChange(
                file_path=str(file.path),
                relative_path=str(file.relative_path),
                original_css=original_css,
                refactored_css=result.refactored_css,
                tokens_used=result.tokens_used,
                lines_added=diff_stats['added'],
                lines_removed=diff_stats['removed'],
                status='pending'
            )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_file, file): file for file in self.files}
            for future in as_completed(futures):
                file = futures[future]
                with session_lock:
                    completed_count[0] += 1
                    if splash:
                        splash.set_status(f"Processing {file.relative_path}")
                        splash.set_progress(completed_count[0], len(self.files))
                try:
                    change = future.result()
                    if change is not None:
                        with session_lock:
                            self.session.add_change(change)
                except Exception:
                    continue

        if splash:
            splash.set_progress(len(self.files), len(self.files))

        if len(self.session.changes) == 0:
            return 'no_changes'

        return True

    def resume(self):
        """Resume a previously saved session, skipping AI processing"""
        try:
            self.session = RefactoringSession.load(target_dir=self.target_dir)
        except FileNotFoundError:
            self.console.print("[red]✗ No saved session found. Run 'dsg start' to begin.[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]✗ Failed to load session: {e}[/red]")
            return False

        pending = self.session.get_pending_changes()
        self.console.print(f"[green]✓ Resumed session: {len(self.session.changes)} files, {len(pending)} pending review[/green]\n")

        if self.auto_apply:
            self._auto_apply_all()
        else:
            self._review_changes()

        return True

    def _review_changes(self):
        """Review all changes interactively with three-column layout"""
        # Use interactive reviewer with rules file
        reviewer = InteractiveReviewer(self.session.changes, self.diff_generator, rules_file=self.rules_file)
        decisions = reviewer.review_all()
        
        # Update session with decisions
        for index, decision in decisions.items():
            if decision in ['accepted', 'rejected', 'skipped']:
                self.session.update_status(index, decision)
            elif decision == 'quit':
                self.session.save()
                return
        
        # Apply accepted changes
        self._apply_changes()
    
    def _apply_changes(self):
        """Apply accepted changes to files"""
        accepted = self.session.get_accepted_changes()
        
        if not accepted:
            self.console.print("\n[yellow]No changes to apply.[/yellow]")
            self._show_summary()
            return
        
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold cyan]💾 Applying Changes[/bold cyan]")
        self.console.print("=" * 60)
        
        success_count = 0
        
        for change in accepted:
            if self.dry_run:
                self.console.print(f"[yellow]Would write: {change.relative_path}[/yellow]")
                success_count += 1
            else:
                result = self.writer.write(
                    Path(change.file_path),
                    change.refactored_css,
                    create_backup=True
                )
                
                if result.success:
                    self.console.print(f"[green]✓ {change.relative_path}[/green]")
                    if result.backup_path:
                        try:
                            backup_display = result.backup_path.relative_to(Path.cwd())
                        except ValueError:
                            backup_display = result.backup_path
                        self.console.print(f"  [dim]Backup: {backup_display}[/dim]")
                    success_count += 1
                else:
                    self.console.print(f"[red]✗ {change.relative_path}: {result.error}[/red]")
        
        self.console.print(f"\n[green]✓ Applied {success_count}/{len(accepted)} changes[/green]")
        self._show_summary()
    
    def _auto_apply_all(self):
        """Auto-apply all changes without review"""
        for i in range(len(self.session.changes)):
            self.session.update_status(i, 'accepted')
        
        self._apply_changes()
    
    def _show_summary(self):
        """Show final summary"""
        stats = self.session.get_stats()
        
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold cyan]📊 Summary[/bold cyan]")
        self.console.print("=" * 60)
        
        self.console.print(f"Total files: {stats['total']}")
        self.console.print(f"[green]Accepted: {stats['accepted']}[/green]")
        self.console.print(f"[red]Rejected: {stats['rejected']}[/red]")
        self.console.print(f"[yellow]Skipped: {stats['skipped']}[/yellow]")
        self.console.print(f"\nTotal tokens used: {stats['total_tokens']}")
        
        if self.dry_run:
            self.console.print("\n[yellow]This was a dry run - no files were modified.[/yellow]")
        elif stats['accepted'] > 0:
            backup_size = self.writer.get_backup_size()
            self.console.print(f"\nBackup size: {format_size(backup_size)}")
            self.console.print(f"Backup location: [cyan].ds_guardian_backup/[/cyan]")
        
        # Clean up session file
        self.session.clear()
        self.console.print("\n[dim]Session file cleared.[/dim]")
