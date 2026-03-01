"""
Main Refactoring Workflow
Orchestrates the entire refactoring process
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ds_guardian.core.scanner import FileScanner, format_size
from ds_guardian.core.rules import RulesParser
from ds_guardian.core.session import RefactoringSession, FileChange
from ds_guardian.core.writer import FileWriter
from ds_guardian.ai.client import OllamaClient
from ds_guardian.ai.refactorer import CSSRefactorer
from ds_guardian.ai.optimizer import PromptOptimizer
from ds_guardian.ui.diff import DiffGenerator
from ds_guardian.ui.review import InteractiveReviewer
from ds_guardian.ui.splash import SplashScreen


class RefactoringWorkflow:
    """Manages a complete refactoring workflow"""
    
    def __init__(self, target_dir: str, rules_file: str, dry_run: bool = False, auto_apply: bool = False, max_workers: int = 3, model: str = 'qwen2.5-coder:0.5b'):
        """
        Initialize refactoring workflow
        
        Args:
            target_dir: Directory to scan
            rules_file: Path to rules.md
            dry_run: Preview only, don't write files
            auto_apply: Apply all changes without review
            max_workers: Number of parallel workers for AI processing (default: 3)
            model: Ollama model to use (default: llama3.2:3b)
        """
        self.target_dir = Path(target_dir)
        self.rules_file = rules_file
        self.dry_run = dry_run
        self.auto_apply = auto_apply
        self.max_workers = max_workers
        self.model = model
        
        self.console = Console()
        self.scanner = FileScanner(target_dir)
        self.diff_generator = DiffGenerator()
        self.writer = FileWriter()
        self.session = RefactoringSession()
        self.optimizer = PromptOptimizer()
        
        self.files = []
        self.rules = None
        self.client = None
        self.refactorer = None
    
    def run(self):
        """Run the complete refactoring workflow"""
        try:
            # Show splash screen while processing in background
            splash = SplashScreen(self.console)
            
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
                    try:
                        if not self._initialize_ai():
                            return False
                    except Exception as e:
                        return False
                    
                    splash.set_status("Processing files...")
                    splash.set_progress(0, len(self.files))
                    if not self._process_all_files(splash):
                        return False
                    
                    splash.set_status(f"Done — {len(self.session.changes)} files with changes")
                    return True
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return False
            
            # Show splash while processing (up to 60 seconds)
            success = splash.show(duration=60.0, background_task=background_processing)
            
            # Clear screen after splash
            self.console.clear()
            
            if not success:
                self.console.print("[red]✗ Initialization failed during splash screen[/red]")
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
        except Exception:
            return False
        
        if not self.files:
            return False
        
        return True
    
    def _load_rules(self) -> bool:
        """Load design system rules (silent for background processing)"""
        try:
            parser = RulesParser(self.rules_file)
            self.rules = parser.parse()
        except Exception:
            return False
        
        return True
    
    def _initialize_ai(self) -> bool:
        """Initialize AI client and refactorer (runs silently in background)"""
        try:
            print(f"DEBUG: Creating OllamaClient with model={self.model}")
            self.client = OllamaClient(model=self.model)
            
            print("DEBUG: Checking connection...")
            if not self.client.is_available():
                print("DEBUG: is_available() returned False")
                return False
            
            print("DEBUG: Creating CSSRefactorer...")
            self.refactorer = CSSRefactorer(self.client)
            print("DEBUG: AI initialization complete")
            return True
            
        except Exception as e:
            print(f"DEBUG: Exception in _initialize_ai: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_all_files(self, splash=None):
        """Process all files individually with optimized prompts (runs silently in background)"""
        # Collect all CSS content for token optimization
        all_css_content = ""
        for file in self.files:
            with open(file.path, 'r', encoding='utf-8') as f:
                all_css_content += f.read() + "\n"
        
        # Filter tokens to only relevant ones
        filtered_rules = self.optimizer.filter_relevant_tokens(all_css_content, self.rules)
        
        # Generate prompt context with filtered tokens
        design_tokens = RulesParser(self.rules_file).generate_prompt_context(filtered_rules)
        
        # Process files individually
        for idx, file in enumerate(self.files):
            if splash:
                splash.set_status(f"Processing {file.relative_path}")
                splash.set_progress(idx, len(self.files))

            # Read file content
            with open(file.path, 'r', encoding='utf-8') as f:
                original_css = f.read()
            
            # Refactor
            result = self.refactorer.refactor(original_css, design_tokens)
            
            if not result.success:
                continue
            
            # Generate diff stats
            diff_lines = self.diff_generator.generate(original_css, result.refactored_css)
            diff_stats = self.diff_generator.get_stats(diff_lines)
            
            if not diff_stats['has_changes']:
                continue
            
            # Create file change record
            change = FileChange(
                file_path=str(file.path),
                relative_path=str(file.relative_path),
                original_css=original_css,
                refactored_css=result.refactored_css,
                tokens_used=result.tokens_used,
                lines_added=diff_stats['added'],
                lines_removed=diff_stats['removed'],
                status='pending'
            )
            
            self.session.add_change(change)

        if splash:
            splash.set_progress(len(self.files), len(self.files))
        
        if len(self.session.changes) == 0:
            return False
        
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
                        self.console.print(f"  [dim]Backup: {result.backup_path.relative_to(Path.cwd())}[/dim]")
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
