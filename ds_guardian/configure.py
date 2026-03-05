"""
Interactive model configuration wizard.
Invoked via: dsg --model-configure
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ds_guardian.ai.config import (
    ModelConfig,
    PROVIDERS,
    PROVIDER_DEFAULTS,
    PROVIDER_ENV_VARS,
    PROVIDER_PACKAGES,
    CONFIG_PATH,
)


class ModelConfigurator:
    """Interactive wizard to configure the AI provider"""

    def __init__(self):
        self.console = Console()

    def run(self):
        """Run the full configuration wizard"""
        self.console.print()
        self.console.print(Panel(
            "[bold cyan]DS Guardian — AI Model Configuration[/bold cyan]\n"
            "[dim]Configure which AI provider and model to use.[/dim]",
            expand=False,
        ))

        # Show current config if it exists
        current = ModelConfig.load()
        if ModelConfig.exists():
            self.console.print("\n[bold]Current configuration:[/bold]")
            self.console.print(current.display())
            self.console.print()

        # ── Step 1: choose provider ──────────────────────────────────── #
        self.console.print("[bold]Available providers:[/bold]")
        provider_descriptions = {
            'ollama':    'Local model via Ollama (free, no API key needed)',
            'anthropic': 'Anthropic Claude (requires ANTHROPIC_API_KEY)',
            'openai':    'OpenAI GPT (requires OPENAI_API_KEY)',
            'gemini':    'Google Gemini (requires GEMINI_API_KEY)',
        }
        for i, p in enumerate(PROVIDERS, 1):
            marker = "[green]●[/green]" if p == current.provider else " "
            self.console.print(f"  {marker} [bold]{i}.[/bold] {p:12s} — {provider_descriptions[p]}")

        self.console.print()
        provider_choice = Prompt.ask(
            "Choose provider",
            choices=[str(i) for i in range(1, len(PROVIDERS) + 1)],
            default=str(PROVIDERS.index(current.provider) + 1),
        )
        provider = PROVIDERS[int(provider_choice) - 1]

        # ── Step 2: choose model ─────────────────────────────────────── #
        default_model = PROVIDER_DEFAULTS[provider]
        self.console.print()

        if provider == 'ollama':
            self.console.print(f"[dim]Default model: {default_model}[/dim]")
            self.console.print("[dim]You can use any model you have pulled locally (e.g. llama3.2, mistral).[/dim]")
        else:
            self._print_model_suggestions(provider)

        model = Prompt.ask(
            "Model name",
            default=current.model if current.provider == provider else default_model,
        )

        # ── Step 3: API key (cloud providers only) ───────────────────── #
        api_key = None
        if provider != 'ollama':
            env_var = PROVIDER_ENV_VARS[provider]
            package = PROVIDER_PACKAGES[provider]

            self.console.print()
            self.console.print(
                f"[dim]API key for {provider}. Leave blank to use the "
                f"[bold]{env_var}[/bold] environment variable instead.[/dim]"
            )

            existing_key = current.api_key if current.provider == provider else None
            if existing_key:
                masked = existing_key[:6] + '*' * max(0, len(existing_key) - 6)
                self.console.print(f"[dim]Current stored key: {masked}[/dim]")
                if not Confirm.ask("Replace stored API key?", default=False):
                    api_key = existing_key
                else:
                    api_key = Prompt.ask("API key", password=True, default="") or None
            else:
                api_key = Prompt.ask("API key (or press Enter to use env var)", password=True, default="") or None

            # SDK install reminder
            self._check_sdk(package, provider)

        # ── Step 4: confirm and save ─────────────────────────────────── #
        config = ModelConfig(provider=provider, model=model, api_key=api_key)

        self.console.print()
        self.console.print("[bold]New configuration:[/bold]")
        self.console.print(config.display())
        self.console.print()

        if Confirm.ask("Save this configuration?", default=True):
            config.save()
            self.console.print(
                f"\n[green]✓ Configuration saved to [bold]{CONFIG_PATH}[/bold][/green]"
            )
            self.console.print("[dim]Run 'dsg --check-setup' to verify everything is ready.[/dim]\n")
        else:
            self.console.print("\n[yellow]Configuration not saved.[/yellow]\n")

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _print_model_suggestions(self, provider: str):
        suggestions = {
            'anthropic': [
                ('claude-3-5-haiku-latest',   'Fast and cheap — recommended default'),
                ('claude-3-5-sonnet-latest',  'Smarter, higher quality'),
                ('claude-3-opus-latest',      'Most capable, most expensive'),
            ],
            'openai': [
                ('gpt-4o-mini',  'Fast and cheap — recommended default'),
                ('gpt-4o',       'Smarter, higher quality'),
                ('o3-mini',      'Reasoning model'),
            ],
            'gemini': [
                ('gemini-1.5-flash',   'Fast and cheap — recommended default'),
                ('gemini-2.0-flash',   'Newer, faster'),
                ('gemini-1.5-pro',     'Higher quality'),
            ],
        }
        self.console.print(f"[dim]Common {provider} models:[/dim]")
        for name, desc in suggestions.get(provider, []):
            self.console.print(f"  [dim]• {name:40s} {desc}[/dim]")

    def _check_sdk(self, package: str, provider: str):
        try:
            from importlib.metadata import version
            version(package)
        except Exception:
            self.console.print()
            self.console.print(
                f"[yellow]⚠ The [bold]{package}[/bold] SDK is not installed.[/yellow]\n"
                f"  Run: [bold cyan]pip install \"ds-guardian[{provider}]\"[/bold cyan]"
            )
