"""
Analysis Report UI
Renders the design-system health report in the terminal using Rich.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich import box

from ds_guardian.ai.analyzer import ScriptMetrics, AnalysisResult


class AnalysisReportRenderer:
    """Renders the three-section analysis report to the terminal"""

    def __init__(self, console: Console):
        self.console = console

    def render(
        self,
        metrics: ScriptMetrics,
        ai_result: AnalysisResult,
        target_dir: str,
        rules_file: str,
    ):
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Design System Health Report[/bold]\n"
                f"[dim]Target:[/dim] {target_dir}   "
                f"[dim]Tokens file:[/dim] {rules_file}",
                style="cyan",
                padding=(0, 2),
            )
        )
        self.console.print()

        self._render_metrics(metrics)
        self.console.print()

        if ai_result.success:
            self._render_ai_section("Analysis", ai_result.analysis, "yellow")
            self.console.print()
            self._render_ai_section("Proposals", ai_result.proposals, "green")
        else:
            self.console.print(f"[red]✗ AI analysis failed: {ai_result.error}[/red]")

        self.console.print()

    def _render_metrics(self, metrics: ScriptMetrics):
        self.console.print(Rule("[bold cyan]Metrics[/bold cyan]", style="cyan"))
        self.console.print()

        # Coverage summary row
        cov_color = "green" if metrics.coverage_pct >= 80 else "yellow" if metrics.coverage_pct >= 50 else "red"
        self.console.print(
            f"  Coverage: [{cov_color}]{metrics.coverage_pct:.1f}%[/{cov_color}] "
            f"[dim]({metrics.covered_occurrences}/{metrics.total_value_occurrences} "
            f"hardcoded value occurrences already have a token)[/dim]"
        )
        self.console.print(
            f"  Tokens defined: [cyan]{metrics.total_tokens_defined}[/cyan]"
        )
        self.console.print()

        # Tables for orphans, unused, duplicates
        if metrics.orphaned_values:
            self._render_orphans_table(metrics.orphaned_values)
            self.console.print()

        if metrics.unused_tokens:
            self._render_unused_table(metrics.unused_tokens)
            self.console.print()

        if metrics.duplicate_tokens:
            self._render_duplicates_table(metrics.duplicate_tokens)

    def _render_orphans_table(self, orphans):
        table = Table(
            title=f"Orphaned Values — hardcoded with no token ({len(orphans)} found)",
            box=box.SIMPLE_HEAD,
            title_style="bold yellow",
            header_style="bold",
            show_lines=False,
        )
        table.add_column("Value", style="cyan", no_wrap=True)
        table.add_column("Freq", justify="right", style="yellow")
        table.add_column("Used in", style="dim")

        for o in orphans[:20]:
            table.add_row(
                o["value"],
                str(o["frequency"]),
                ", ".join(o["properties"]),
            )
        if len(orphans) > 20:
            table.add_row(f"[dim]… {len(orphans) - 20} more[/dim]", "", "")

        self.console.print(table)

    def _render_unused_table(self, unused_tokens):
        table = Table(
            title=f"Unused Tokens — defined but never found in codebase ({len(unused_tokens)} found)",
            box=box.SIMPLE_HEAD,
            title_style="bold red",
            header_style="bold",
        )
        table.add_column("Token name", style="red")

        for name in unused_tokens[:20]:
            table.add_row(name)
        if len(unused_tokens) > 20:
            table.add_row(f"[dim]… {len(unused_tokens) - 20} more[/dim]")

        self.console.print(table)

    def _render_duplicates_table(self, duplicates):
        table = Table(
            title=f"Duplicate Tokens — same value, different names ({len(duplicates)} found)",
            box=box.SIMPLE_HEAD,
            title_style="bold magenta",
            header_style="bold",
        )
        table.add_column("Value", style="cyan", no_wrap=True)
        table.add_column("Token names", style="magenta")

        for dup in duplicates[:15]:
            table.add_row(dup["value"], ", ".join(dup["tokens"]))

        self.console.print(table)

    def _render_ai_section(self, title: str, content: str, color: str):
        if not content:
            return
        self.console.print(Rule(f"[bold {color}]AI {title}[/bold {color}]", style=color))
        self.console.print()
        # Render line by line, highlighting RENAME / MERGE / ADD / REMOVE / RESTRUCTURE
        for line in content.splitlines():
            rendered = _highlight_proposals(line)
            self.console.print(f"  {rendered}")


def _highlight_proposals(line: str) -> str:
    """Add Rich markup to proposal keywords for visual clarity"""
    keywords = {
        "RENAME:": "[bold cyan]RENAME:[/bold cyan]",
        "MERGE:": "[bold magenta]MERGE:[/bold magenta]",
        "ADD:": "[bold green]ADD:[/bold green]",
        "REMOVE:": "[bold red]REMOVE:[/bold red]",
        "RESTRUCTURE:": "[bold yellow]RESTRUCTURE:[/bold yellow]",
    }
    for kw, replacement in keywords.items():
        if line.strip().startswith(kw):
            return replacement + line[line.index(kw) + len(kw):]
    return line
