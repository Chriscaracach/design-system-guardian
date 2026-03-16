"""
Analyze Workflow
Orchestrates the design-system health analysis: script metrics + AI insights + proposals.
"""

from pathlib import Path
from rich.console import Console

from ds_guardian.core.scanner import FileScanner
from ds_guardian.core.rules import RulesParser
from ds_guardian.core.value_analyzer import CSSValueAnalyzer
from ds_guardian.ai.client import OllamaClient
from ds_guardian.ai.anthropic_client import AnthropicClient
from ds_guardian.ai.openai_client import OpenAIClient
from ds_guardian.ai.gemini_client import GeminiClient
from ds_guardian.ai.config import ModelConfig
from ds_guardian.ai.analyzer import DesignSystemAnalyzer, AnalysisResult, ScriptMetrics
from ds_guardian.ui.analysis_report import AnalysisReportRenderer
from ds_guardian.ui.splash import SplashScreen


class AnalyzeWorkflow:
    """
    Runs the full dsg analyze pipeline:
      1. Scan CSS files
      2. Load design tokens (design-system.css)
      3. Build structured value map (script, no AI)
      4. Compute metrics (script, no AI)
      5. Run AI analysis + proposals
      6. Render report
    """

    def __init__(
        self,
        target_dir: str,
        rules_file: str = 'design_system.css',
        model_config: ModelConfig = None,
    ):
        self.target_dir = Path(target_dir).resolve()

        rules_path = Path(rules_file)
        if not rules_path.is_absolute() and rules_path.parent == Path('.'):
            self.rules_file = str(self.target_dir / rules_path.name)
        else:
            self.rules_file = str(rules_path)

        self.model_config = model_config or ModelConfig.load()

        self.console = Console()
        self.scanner = FileScanner(str(self.target_dir))
        self.value_analyzer = CSSValueAnalyzer()
        self.renderer = AnalysisReportRenderer(self.console)

        self._bg_error = None
        self._metrics = None
        self._ai_result = None
        self._files = []

    def run(self) -> bool:
        """Run the full analysis workflow"""
        try:
            splash = SplashScreen(self.console)

            def background_processing():
                try:
                    splash.set_status("Scanning CSS files...")
                    self._files = self.scanner.scan()
                    if not self._files:
                        self._bg_error = f"No CSS/SCSS/LESS files found in: {self.target_dir}"
                        return False

                    splash.set_status("Loading design tokens...")
                    try:
                        parser = RulesParser(self.rules_file)
                        rules = parser.parse()
                    except FileNotFoundError:
                        self._bg_error = (
                            f"Design system file not found: '{self.rules_file}'\n"
                            "Run 'dsg extract' to generate one, or pass --rules <path>."
                        )
                        return False

                    if rules.get_token_count() == 0:
                        self._bg_error = (
                            f"No design tokens found in '{self.rules_file}'. "
                            "Check that it has :root { --token: value; } blocks."
                        )
                        return False

                    splash.set_status("Analysing CSS values...")
                    value_map = self.value_analyzer.analyze_files(self._files)
                    splash.set_progress(len(self._files) // 2, len(self._files))

                    splash.set_status("Computing metrics...")
                    analyzer = self._make_analyzer()
                    if analyzer is None:
                        return False

                    self._metrics = analyzer.compute_metrics(value_map, rules)
                    self._metrics.files_analysed = len(self._files)

                    splash.set_status("Running AI analysis...")
                    self._ai_result = analyzer.analyse(value_map, rules, self._metrics)
                    splash.set_progress(len(self._files), len(self._files))
                    splash.set_status("Done")
                    return True

                except Exception as e:
                    self._bg_error = str(e)
                    return False

            success = splash.show(duration=120.0, background_task=background_processing)
            self.console.clear()

            if not success:
                msg = self._bg_error or "Analysis failed. Run 'dsg check-setup' to diagnose."
                self.console.print(f"[red]✗ {msg}[/red]")
                return False

            self.renderer.render(
                metrics=self._metrics,
                ai_result=self._ai_result,
                target_dir=str(self.target_dir),
                rules_file=self.rules_file,
            )
            return True

        except KeyboardInterrupt:
            self.console.print("\n[yellow]✗ Interrupted by user[/yellow]")
            return False
        except Exception as e:
            self.console.print(f"\n[red]✗ Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            return False

    def _make_analyzer(self):
        """Initialise the correct AI client and return a DesignSystemAnalyzer"""
        try:
            cfg = self.model_config
            api_key = cfg.resolved_api_key()

            if cfg.provider == 'anthropic':
                client = AnthropicClient(api_key=api_key, model=cfg.model)
                unavailable = (
                    "Anthropic client unavailable. Check the 'anthropic' package is installed "
                    "and ANTHROPIC_API_KEY is set."
                )
            elif cfg.provider == 'openai':
                client = OpenAIClient(api_key=api_key, model=cfg.model)
                unavailable = (
                    "OpenAI client unavailable. Check the 'openai' package is installed "
                    "and OPENAI_API_KEY is set."
                )
            elif cfg.provider == 'gemini':
                client = GeminiClient(api_key=api_key, model=cfg.model)
                unavailable = (
                    "Gemini client unavailable. Check the 'google-generativeai' package is installed "
                    "and GEMINI_API_KEY is set."
                )
            else:
                client = OllamaClient(model=cfg.model)
                unavailable = "Could not connect to Ollama. Is it running? Try: ollama serve"

            if not client.is_available():
                self._bg_error = unavailable
                return None

            return DesignSystemAnalyzer(client)

        except Exception as e:
            self._bg_error = f"AI initialisation error: {e}"
            return None
