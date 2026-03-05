"""
Info command — shows what will happen when 'dsg start' runs in a directory.
Invoked via: dsg info [target]
"""

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ds_guardian.ai.config import ModelConfig, PROVIDER_PACKAGES, PROVIDER_ENV_VARS
from ds_guardian.core.scanner import FileScanner, format_size
from ds_guardian.core.rules import RulesParser
from ds_guardian.core.session import RefactoringSession


class InfoCommand:
    """Displays a pre-flight summary for a target directory"""

    def __init__(self, target_dir: str = '.', rules_file: str = 'design_system.css'):
        self.target_dir = Path(target_dir).resolve()
        rules_path = Path(rules_file)
        if not rules_path.is_absolute() and rules_path.parent == Path('.'):
            self.rules_file = self.target_dir / rules_path.name
        else:
            self.rules_file = Path(rules_file)
        self.console = Console()
        self.model_config = ModelConfig.load()

    def run(self):
        self.console.print()
        self.console.print(Panel(
            f"[bold cyan]DS Guardian — Pre-flight Info[/bold cyan]\n"
            f"[dim]What will happen when you run [bold]dsg start[/bold] here[/dim]",
            expand=False,
        ))

        self._section_ai()
        self._section_target()
        self._section_rules()
        self._section_session()
        self._summary()

    # ------------------------------------------------------------------ #
    # Sections                                                             #
    # ------------------------------------------------------------------ #

    def _section_ai(self):
        self.console.print("\n[bold]AI Provider[/bold]")

        cfg = self.model_config
        provider = cfg.provider
        model = cfg.model

        if not ModelConfig.exists():
            self.console.print(
                "  [yellow]⚠ No configuration found — using defaults (Ollama)[/yellow]\n"
                "  [dim]Run [bold]dsg --model-configure[/bold] to set your preferred provider.[/dim]"
            )
        else:
            self.console.print(f"  [green]✓[/green] Provider : [bold]{provider}[/bold]")
            self.console.print(f"  [green]✓[/green] Model    : [bold]{model}[/bold]")

        if provider == 'ollama':
            self._check_ollama()
        else:
            self._check_cloud_provider(provider, cfg)

    def _check_ollama(self):
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self.console.print("  [green]✓[/green] Ollama   : running")
            else:
                self.console.print("  [red]✗[/red] Ollama   : not responding — run [bold]ollama serve[/bold]")
        except Exception:
            self.console.print("  [red]✗[/red] Ollama   : not reachable — run [bold]ollama serve[/bold]")

    def _check_cloud_provider(self, provider: str, cfg: ModelConfig):
        package = PROVIDER_PACKAGES.get(provider, '')
        env_var = PROVIDER_ENV_VARS.get(provider, '')

        # SDK check
        try:
            from importlib.metadata import version
            ver = version(package)
            self.console.print(f"  [green]✓[/green] SDK      : {package} {ver}")
        except Exception:
            self.console.print(
                f"  [red]✗[/red] SDK      : [bold]{package}[/bold] not installed — "
                f"run [bold cyan]pip install \"ds-guardian[{provider}]\"[/bold cyan]"
            )

        # API key check
        key = cfg.resolved_api_key()
        if key:
            masked = key[:6] + '*' * max(0, len(key) - 6)
            self.console.print(f"  [green]✓[/green] API key  : {masked} (via {'config' if cfg.api_key else env_var})")
        else:
            self.console.print(
                f"  [red]✗[/red] API key  : not set — store it with [bold]dsg --model-configure[/bold] "
                f"or export [bold]{env_var}[/bold]"
            )

    def _section_target(self):
        self.console.print(f"\n[bold]Target Directory[/bold]")
        self.console.print(f"  [dim]{self.target_dir}[/dim]")

        if not self.target_dir.exists():
            self.console.print("  [red]✗[/red] Directory does not exist")
            return

        try:
            scanner = FileScanner(str(self.target_dir))
            files = scanner.scan()
        except Exception as e:
            self.console.print(f"  [red]✗[/red] Could not scan: {e}")
            return

        if not files:
            self.console.print("  [yellow]⚠[/yellow] No CSS/SCSS/SASS/LESS files found — nothing to refactor")
            return

        summary = scanner.get_summary(files)
        total = summary['total_files']
        size = format_size(summary['total_size'])

        self.console.print(f"  [green]✓[/green] Found [bold]{total}[/bold] style file{'s' if total != 1 else ''} ({size} total)")

        # Breakdown by extension
        table = Table(box=box.SIMPLE, show_header=True, pad_edge=False)
        table.add_column("Extension", style="cyan", no_wrap=True)
        table.add_column("Files", justify="right")
        table.add_column("Size", justify="right", style="dim")

        for ext, data in sorted(summary['by_extension'].items()):
            table.add_row(ext, str(data['count']), format_size(data['size']))

        self.console.print(table)

        if summary['largest_file']:
            lf = summary['largest_file']
            self.console.print(
                f"  [dim]Largest: {lf.relative_path} ({format_size(lf.size)})[/dim]"
            )

    def _section_rules(self):
        self.console.print(f"\n[bold]Rules File (Design Tokens)[/bold]")
        self.console.print(f"  [dim]{self.rules_file}[/dim]")

        if not self.rules_file.exists():
            self.console.print(
                "  [red]✗[/red] File not found — create one with [bold]dsg extract[/bold] "
                "or pass [bold]--rules <path>[/bold]"
            )
            return

        try:
            parser = RulesParser(str(self.rules_file))
            rules = parser.parse()
        except Exception as e:
            self.console.print(f"  [red]✗[/red] Could not parse rules file: {e}")
            return

        total_tokens = rules.get_token_count()
        if total_tokens == 0:
            self.console.print("  [yellow]⚠[/yellow] File found but no tokens parsed — check the format")
            return

        self.console.print(f"  [green]✓[/green] [bold]{total_tokens}[/bold] design token{'s' if total_tokens != 1 else ''} loaded")

        # Per-category breakdown
        categories = {
            'Colors':      rules.colors,
            'Spacing':     rules.spacing,
            'Typography':  rules.typography,
            'Borders':     rules.borders,
            'Shadows':     rules.shadows,
            'Breakpoints': rules.breakpoints,
        }
        for label, cat in rules.custom.items():
            categories[label.title()] = cat

        table = Table(box=box.SIMPLE, show_header=True, pad_edge=False)
        table.add_column("Category", style="cyan")
        table.add_column("Tokens", justify="right")

        for label, tokens in categories.items():
            if tokens:
                table.add_row(label, str(len(tokens)))

        self.console.print(table)

    def _section_session(self):
        session = RefactoringSession(target_dir=self.target_dir)
        if not session.exists():
            return

        self.console.print("\n[bold]Saved Session[/bold]")
        try:
            loaded = RefactoringSession.load(target_dir=self.target_dir)
            stats = loaded.get_stats()
            pending = stats['pending']
            total = stats['total']
            created = loaded.metadata.get('created_at', 'unknown')[:19].replace('T', ' ')
            self.console.print(
                f"  [yellow]⚠[/yellow] A session from [bold]{created}[/bold] exists — "
                f"[bold]{pending}[/bold] of [bold]{total}[/bold] files pending review"
            )
            self.console.print(
                "  [dim]Running [bold]dsg start[/bold] will prompt to resume or discard it.[/dim]"
            )
        except Exception:
            self.console.print("  [yellow]⚠[/yellow] A session file exists but could not be read")

    def _summary(self):
        self.console.print("\n" + "─" * 50)

        cfg = self.model_config
        provider_ready = self._is_provider_ready(cfg)

        rules_ok = self.rules_file.exists()
        try:
            if rules_ok:
                rules_ok = RulesParser(str(self.rules_file)).parse().get_token_count() > 0
        except Exception:
            rules_ok = False

        has_files = False
        try:
            files = FileScanner(str(self.target_dir)).scan()
            has_files = len(files) > 0
        except Exception:
            pass

        if provider_ready and rules_ok and has_files:
            self.console.print(
                f"\n[bold green]✓ Ready.[/bold green] "
                f"Running [bold]dsg start[/bold] will process style files using "
                f"[bold]{cfg.provider}[/bold] / [bold]{cfg.model}[/bold].\n"
            )
        else:
            issues = []
            if not provider_ready:
                issues.append("AI provider is not ready (see above)")
            if not rules_ok:
                issues.append("no valid rules file found — run [bold]dsg extract[/bold] first")
            if not has_files:
                issues.append("no style files found in target directory")
            self.console.print("\n[bold red]✗ Not ready.[/bold red] Fix the following before running:")
            for issue in issues:
                self.console.print(f"  • {issue}")
            self.console.print()

    def _is_provider_ready(self, cfg: ModelConfig) -> bool:
        if cfg.provider == 'ollama':
            try:
                import requests
                r = requests.get("http://localhost:11434/api/tags", timeout=2)
                return r.status_code == 200
            except Exception:
                return False
        else:
            package = PROVIDER_PACKAGES.get(cfg.provider, '')
            try:
                from importlib.metadata import version
                version(package)
            except Exception:
                return False
            return bool(cfg.resolved_api_key())
