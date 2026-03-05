# DS Guardian

**DS Guardian** is an AI-powered CLI tool that automatically refactors CSS files to use design system tokens (CSS variables). Point it at your project, provide your design token rules, and it will replace hardcoded values with the right CSS variables — letting you review every change before it's applied.

---

## How it works

1. **Scan** — finds all `.css`, `.scss`, `.sass`, and `.less` files in your target directory
2. **Process** — sends each file to an AI model (local or cloud) along with your design token rules
3. **Review** — presents a side-by-side diff for each changed file; you accept, reject, or skip each one
4. **Apply** — writes the accepted changes and creates backups of originals

---

## Requirements

- Python 3.10+
- **One of the following AI backends:**
  - [Ollama](https://ollama.com) running locally (default, free, no API key)
  - Anthropic API key → Claude
  - OpenAI API key → GPT
  - Google AI API key → Gemini

---

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd ds-guardian

# Create a virtual environment and install
python -m venv venv
source venv/bin/activate
pip install -e .

# Verify setup (uses Ollama by default)
dsg check-setup

# Configure a different AI provider (interactive wizard)
dsg configure
```

This installs the `dsg` command globally via `~/.local/bin`. If that directory
isn't on your PATH yet, add it to your shell config (fish: `fish_add_path ~/.local/bin`).

---

## Usage

```bash
# Pre-flight summary: see what dsg start will do before running it
dsg info
dsg info /path/to/your/project

# Refactor the current directory (uses Ollama by default)
dsg start

# Refactor a specific project
dsg start /path/to/your/project

# Preview changes without writing files
dsg start --dry-run

# Apply all changes without manual review
dsg start --auto-apply

# Use a custom rules file
dsg start --rules /path/to/my-tokens.md

# Verify your environment
dsg check-setup
```

### Configuring the AI provider

Run the interactive wizard once to choose your provider, model, and API key:

```bash
dsg configure
```

The wizard walks you through:

1. **Provider** — `ollama`, `anthropic`, `openai`, or `gemini`
2. **Model** — with suggestions per provider
3. **API key** — stored in `~/.config/ds_guardian/model.json` (cloud providers only)

Configuration is saved globally and used by all subsequent `dsg` commands. After configuring, verify the setup:

```bash
dsg check-setup
```

| Provider    | Default model             | SDK to install                         | Env var (alternative to stored key) |
| ----------- | ------------------------- | -------------------------------------- | ----------------------------------- |
| `ollama`    | `qwen2.5-coder:0.5b`      | — (local)                              | —                                   |
| `anthropic` | `claude-3-5-haiku-latest` | `pip install "ds-guardian[anthropic]"` | `ANTHROPIC_API_KEY`                 |
| `openai`    | `gpt-4o-mini`             | `pip install "ds-guardian[openai]"`    | `OPENAI_API_KEY`                    |
| `gemini`    | `gemini-1.5-flash`        | `pip install "ds-guardian[gemini]"`    | `GEMINI_API_KEY`                    |

---

## Rules file (`rules.md`)

DS Guardian reads design tokens from a Markdown file. By default it looks for `rules.md` in the current directory.

Format your tokens under section headers that describe their category:

```markdown
## Colors

--primary: #2563eb
--gray-900: #111827
--white: #ffffff

## Spacing

--space-1: 4px
--space-2: 8px
--space-4: 16px

## Typography

--text-sm: 0.875rem
--font-bold: 700

## Borders

--radius-md: 6px
--radius-full: 9999px
```

DS Guardian auto-detects the category from the header name and filters tokens to only the ones relevant to each file, keeping AI prompts lean.

---

## Interactive review

During review, for each changed file you see a **side-by-side diff** (original left, refactored right) alongside the rules file for reference.

| Key       | Action                               |
| --------- | ------------------------------------ |
| `1`       | Accept this change                   |
| `2`       | Reject this change                   |
| `3`       | Skip (decide later)                  |
| `4`       | Accept all remaining                 |
| `5` / `q` | Save and quit                        |
| `↑` / `k` | Scroll up                            |
| `↓` / `j` | Scroll down                          |
| `Tab`     | Switch between diff and rules panels |

---

## Backups

Every accepted change creates a timestamped backup under `.ds_guardian_backup/` before writing. You can safely re-run the tool.

---

## Project structure

```
ds-guardian/
├── main.py              # CLI entry point (legacy, prefer dsg)
├── rules.md             # Your design token definitions
├── requirements.txt
└── ds_guardian/
    ├── checker.py       # Setup verification
    ├── workflow.py      # Main orchestration
    ├── core/
    │   ├── scanner.py   # File discovery
    │   ├── rules.py     # Token parser
    │   ├── session.py   # Session state
    │   └── writer.py    # File writing & backups
    ├── ai/
    │   ├── client.py        # BaseAIClient + OllamaClient
    │   ├── anthropic_client.py # Anthropic Claude client
    │   ├── openai_client.py    # OpenAI GPT client
    │   ├── gemini_client.py    # Google Gemini client
    │   ├── refactorer.py    # CSS refactoring logic
    │   └── optimizer.py     # Token relevance filtering
    └── ui/
        ├── components.py# TUI building blocks
        ├── diff.py      # Diff generation
        ├── side_by_side.py # Side-by-side view
        ├── pager.py     # Keyboard navigation
        ├── splash.py    # Splash screen
        └── review.py    # Interactive review loop
```

---

## License

MIT
