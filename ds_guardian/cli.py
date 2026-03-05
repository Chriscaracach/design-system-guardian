"""
CLI entry point for DS Guardian.
Registered as the 'dsg' console script via pyproject.toml.
"""

import sys
import argparse
from pathlib import Path


def main():
    """Main entry point for DS Guardian"""
    parser = argparse.ArgumentParser(
        prog="dsg",
        description="DS Guardian — AI-powered CSS design token refactoring tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dsg start                              # Refactor current directory
  dsg start /path/to/project             # Refactor specific directory
  dsg info                               # Pre-flight summary for current directory
  dsg info /path/to/project              # Pre-flight summary for a specific directory
  dsg --check-setup                      # Verify installation
  dsg start --dry-run                    # Preview changes without applying
  dsg extract                            # Extract design tokens from current directory
  dsg extract /path/to/project           # Extract design tokens from specific directory
  dsg start --rules design_system.css    # Use a specific design system file

AI model:
  dsg --model-configure                  # Interactive wizard to set provider, model & API key
  dsg --check-setup                      # Verify the configured provider is ready

Install cloud provider SDKs:
  pip install "ds-guardian[anthropic]"
  pip install "ds-guardian[openai]"
  pip install "ds-guardian[gemini]"
  pip install "ds-guardian[all-providers]"
        """
    )

    # Main command
    parser.add_argument(
        'command',
        nargs='?',
        choices=['start', 'check-setup', 'review', 'extract', 'info'],
        help='Command to run'
    )

    # Positional argument for target directory
    parser.add_argument(
        'target',
        nargs='?',
        default='.',
        help='Target directory to scan (default: current directory)'
    )

    # Flags
    parser.add_argument(
        '--check-setup',
        action='store_true',
        help='Verify installation and setup'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )

    parser.add_argument(
        '--auto-apply',
        action='store_true',
        help='Apply all changes without review'
    )

    parser.add_argument(
        '--no-gifs',
        action='store_true',
        help='Disable GIF animations (use ASCII only)'
    )

    parser.add_argument(
        '--ascii-only',
        action='store_true',
        help='Use only ASCII characters (no Unicode)'
    )

    parser.add_argument(
        '--rules',
        type=str,
        default='design_system.css',
        help='Path to design system file (default: design_system.css)'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=3,
        help='Number of parallel workers for AI processing (default: 3)'
    )

    parser.add_argument(
        '--model-configure',
        action='store_true',
        help='Run the interactive AI model configuration wizard'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory for extracted token files (default: target directory)'
    )

    args = parser.parse_args()

    # Handle model-configure command
    if args.model_configure:
        from ds_guardian.configure import ModelConfigurator
        ModelConfigurator().run()
        return

    # Load persisted model config for all other commands
    from ds_guardian.ai.config import ModelConfig
    model_config = ModelConfig.load()

    # Handle check-setup command
    if args.check_setup or args.command == 'check-setup':
        from ds_guardian.checker import SetupChecker
        checker = SetupChecker(model_config=model_config)
        checker.check_all()
        return

    ascii_only = args.no_gifs or args.ascii_only

    # Handle info command
    if args.command == 'info':
        from ds_guardian.info import InfoCommand
        InfoCommand(target_dir=args.target, rules_file=args.rules).run()
        return

    # Handle review command — resume a saved session
    if args.command == 'review':
        from ds_guardian.workflow import RefactoringWorkflow
        workflow = RefactoringWorkflow(
            target_dir=args.target,
            rules_file=args.rules,
            dry_run=args.dry_run,
            auto_apply=args.auto_apply,
            max_workers=args.workers,
            model_config=model_config,
            ascii_only=ascii_only
        )
        success = workflow.resume()
        sys.exit(0 if success else 1)

    # Handle extract command
    if args.command == 'extract':
        from ds_guardian.extract_workflow import ExtractWorkflow
        target = args.output if args.output else args.target
        workflow = ExtractWorkflow(
            target_dir=target,
            model_config=model_config,
            ascii_only=ascii_only,
        )
        success = workflow.run()
        sys.exit(0 if success else 1)

    # Handle start command
    if args.command == 'start':
        from ds_guardian.workflow import RefactoringWorkflow

        workflow = RefactoringWorkflow(
            target_dir=args.target,
            rules_file=args.rules,
            dry_run=args.dry_run,
            auto_apply=args.auto_apply,
            max_workers=args.workers,
            model_config=model_config,
            ascii_only=ascii_only
        )

        success = workflow.run()
        sys.exit(0 if success else 1)

    # No command specified
    parser.print_help()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
