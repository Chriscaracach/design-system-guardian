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
  dsg start                    # Start refactoring in current directory
  dsg start /path/to/project   # Refactor specific directory
  dsg --check-setup            # Verify installation
  dsg start --dry-run          # Preview changes without applying
        """
    )

    # Main command
    parser.add_argument(
        'command',
        nargs='?',
        choices=['start', 'check-setup'],
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
        default='rules.md',
        help='Path to rules file (default: rules.md)'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=3,
        help='Number of parallel workers for AI processing (default: 3)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='qwen2.5-coder:0.5b',
        help='Ollama model to use (default: qwen2.5-coder:0.5b)'
    )

    args = parser.parse_args()

    # Handle check-setup command
    if args.check_setup or args.command == 'check-setup':
        from css_tool.checker import SetupChecker
        checker = SetupChecker()
        checker.check_all()
        return

    # Handle start command
    if args.command == 'start':
        from css_tool.workflow import RefactoringWorkflow

        workflow = RefactoringWorkflow(
            target_dir=args.target,
            rules_file=args.rules,
            dry_run=args.dry_run,
            auto_apply=args.auto_apply,
            max_workers=args.workers,
            model=args.model
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
