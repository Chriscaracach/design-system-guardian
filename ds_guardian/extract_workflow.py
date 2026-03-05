"""
Extract Workflow
Orchestrates the design system extraction process
"""

from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

from ds_guardian.core.scanner import FileScanner
from ds_guardian.core.extractor import DesignSystemExtractor, CATEGORY_FILES, CATEGORY_ORDER
from ds_guardian.ai.client import OllamaClient
from ds_guardian.ai.extraction_refactorer import CSSExtractionRefactorer
from ds_guardian.ui.extraction_review import ExtractionReviewer
from ds_guardian.ui.splash import SplashScreen


class ExtractWorkflow:
    """Manages the design system extraction workflow"""

    def __init__(
        self,
        target_dir: str,
        model: str = "qwen2.5-coder:0.5b",
    ):
        self.target_dir = Path(target_dir).resolve()
        self.model = model

        self.console = Console()
        self.scanner = FileScanner(target_dir)
        self.ds_extractor = DesignSystemExtractor()
        self.reviewer = ExtractionReviewer(self.console)

        self._bg_error = None
        self._design_system_css = None
        self._extracted = None
        self._files = []
        self._tokens_used = 0

    def run(self) -> bool:
        """Run the extraction workflow"""
        try:
            splash = SplashScreen(self.console)

            def background_processing():
                try:
                    splash.set_status("Scanning CSS files...")
                    self._files = self.scanner.scan()
                    if not self._files:
                        self._bg_error = f"No CSS/SCSS/LESS files found in: {self.target_dir}"
                        return False

                    splash.set_status("Connecting to AI model...")
                    client = OllamaClient(model=self.model)
                    if not client.is_available():
                        self._bg_error = "Could not connect to Ollama. Is it running? Try: ollama serve"
                        return False

                    refactorer = CSSExtractionRefactorer(client)

                    splash.set_status("Reading CSS files...")
                    combined_css = ""
                    for i, f in enumerate(self._files):
                        splash.set_progress(i, len(self._files))
                        try:
                            combined_css += f.path.read_text(encoding="utf-8") + "\n"
                        except Exception:
                            continue

                    splash.set_status("Extracting design tokens with AI...")
                    result = refactorer.extract(combined_css)
                    if not result.success:
                        self._bg_error = f"Extraction failed: {result.error}"
                        return False

                    self._extracted = result.extracted
                    self._tokens_used = result.tokens_used
                    self._design_system_css = self.ds_extractor.build_design_system_css(result.extracted)

                    splash.set_status(f"Done — {result.extracted.total_count()} tokens extracted")
                    splash.set_progress(len(self._files), len(self._files))
                    return True

                except Exception as e:
                    self._bg_error = str(e)
                    return False

            success = splash.show(duration=120.0, background_task=background_processing)
            self.console.clear()

            if not success:
                msg = self._bg_error or "Extraction failed. Run 'dsg --check-setup' to diagnose."
                self.console.print(f"[red]✗ {msg}[/red]")
                return False

            token_count = self._extracted.total_count()
            self.console.print(f"[green]✓ Scanned {len(self._files)} CSS files[/green]")
            self.console.print(f"[green]✓ Extracted {token_count} design tokens[/green]")
            if self._extracted.existing_vars:
                self.console.print(f"[dim]  + {len(self._extracted.existing_vars)} existing CSS variables included[/dim]")
            self.console.print()

            # Phase 2: Review
            accepted = self.reviewer.review(
                self._design_system_css,
                token_count=token_count,
                file_count=len(self._files),
            )

            self.console.clear()

            if not accepted:
                self.console.print("[yellow]✗ Extraction rejected — no files written.[/yellow]")
                return True

            # Phase 3: Confirm before writing
            self.console.print(f"\n[bold]Files to be written in:[/bold] [cyan]{self.target_dir}[/cyan]\n")
            self._list_output_files()

            if not Confirm.ask("\nWrite these files?", default=True):
                self.console.print("[yellow]Cancelled — no files written.[/yellow]")
                return True

            self._write_files()
            return True

        except KeyboardInterrupt:
            self.console.print("\n[yellow]✗ Interrupted by user[/yellow]")
            return False
        except Exception as e:
            self.console.print(f"\n[red]✗ Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            return False

    def _list_output_files(self):
        """Print the list of files that will be written"""
        self.console.print("  [cyan]design_system.css[/cyan] [dim](full consolidated file)[/dim]")
        for cat in CATEGORY_ORDER:
            tokens = self._extracted.tokens_by_category.get(cat, [])
            if not tokens:
                continue
            filename = CATEGORY_FILES[cat]
            self.console.print(f"  [cyan]{filename}[/cyan] [dim]({len(tokens)} tokens)[/dim]")

    def _write_files(self):
        """Write design_system.css and category files"""
        written = []
        errors = []

        # Write design_system.css
        ds_path = self.target_dir / "design_system.css"
        try:
            ds_path.write_text(self._design_system_css, encoding="utf-8")
            written.append("design_system.css")
        except Exception as e:
            errors.append(f"design_system.css: {e}")

        # Write category files
        for cat in CATEGORY_ORDER:
            tokens = self._extracted.tokens_by_category.get(cat, [])
            if not tokens:
                continue
            filename = CATEGORY_FILES[cat]
            cat_path = self.target_dir / filename
            try:
                content = self.ds_extractor.build_category_css(cat, tokens)
                cat_path.write_text(content, encoding="utf-8")
                written.append(filename)
            except Exception as e:
                errors.append(f"{filename}: {e}")

        self.console.print()
        for f in written:
            self.console.print(f"[green]✓ {f}[/green]")
        for e in errors:
            self.console.print(f"[red]✗ {e}[/red]")

        self.console.print(f"\n[green]✓ Written {len(written)} file(s) to {self.target_dir}[/green]")
        self.console.print(f"[dim]Total tokens used by AI: {self._tokens_used}[/dim]")
