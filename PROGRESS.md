# AI Integration Redesign — Progress Notes

Branch: `new-approach`
Plan file: `/home/chris/.windsurf/plans/ai-integration-improvement-e2e07c.md`

## Status: Implementation complete, ready for testing

---

## What was changed

### Guiding principle

> Scripts do mechanical work. AI does analysis.

### New files created

| File                                 | Role                                                                                                                                                                          |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ds_guardian/core/value_analyzer.py` | Shared foundation. Scans all CSS files and builds a `ValueMap`: `value → {frequency, properties used in, example selectors}`. Pure Python, no AI. Used by all three features. |
| `ds_guardian/core/substitutor.py`    | Deterministic refactor engine. 1 token match → replace immediately. 0 matches → skip. 2+ matches → flag as ambiguous for AI.                                                  |
| `ds_guardian/ai/analyzer.py`         | Computes `ScriptMetrics` (coverage %, orphaned values, unused tokens, duplicate tokens) + sends structured prompt to AI for qualitative analysis and concrete proposals.      |
| `ds_guardian/analyze_workflow.py`    | Orchestrates the new `dsg analyze` command end-to-end.                                                                                                                        |
| `ds_guardian/ui/analysis_report.py`  | Rich terminal renderer for the three-section report (Metrics / AI Analysis / AI Proposals).                                                                                   |

### Modified files

| File                                      | Change                                                                                                                                                                                 |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ds_guardian/ai/refactorer.py`            | Replaced `refactor()` (sent full CSS to AI) with `resolve_ambiguous()` — AI only sees declarations where the same value maps to 2+ token candidates, with selector + property context. |
| `ds_guardian/workflow.py`                 | Wired `CSSSubstitutor` first, then optional `resolve_ambiguous()` call. Removed `PromptOptimizer` dependency (no longer needed).                                                       |
| `ds_guardian/ai/extraction_refactorer.py` | Now accepts a `ValueMap` instead of a raw CSS blob. Removed the 12 000-char truncation. Prompt now describes each value with frequency + property + selector context.                  |
| `ds_guardian/extract_workflow.py`         | Runs `CSSValueAnalyzer` before calling AI. Uses `ModelConfig` for all providers (was hardcoded to Ollama).                                                                             |
| `ds_guardian/cli.py`                      | Added `analyze [target]` command.                                                                                                                                                      |

---

## How the three workflows now work

### `dsg start` (refactor)

1. `CSSSubstitutor` scans each file — replaces all exact-match values with `var(--token)` immediately
2. Only files with ambiguous declarations (same value → 2+ tokens) trigger an AI call
3. AI receives: selector, property name, raw value, candidate token names — returns a JSON array of decisions
4. Decisions applied on top of script substitutions
5. Diff review unchanged

### `dsg extract`

1. `CSSValueAnalyzer` builds a `ValueMap` from all CSS files
2. AI receives the structured summary (up to 200 values, sorted by frequency) — not raw CSS
3. AI names tokens using frequency + property + selector context
4. Rest of flow unchanged

### `dsg analyze` (new)

1. Scan files + load `design_system.css`
2. `CSSValueAnalyzer` builds `ValueMap`
3. Script computes: coverage %, orphaned values (freq ≥ 3, no token), unused tokens, duplicate tokens
4. AI receives: metrics summary + token list + value summary → produces Analysis + Proposals
5. Rich report rendered in three sections

---

## Test fixture

`test_fixture/` — small project to test against.

```
test_fixture/
  design_system.css       ← sparse on purpose (few tokens, many gaps)
  src/
    button.css
    card.css
    typography.css
```

The CSS files use hardcoded values, most of which match tokens in `design_system.css`.
The `design_system.css` was intentionally made sparse by the user (many tokens removed)
so that `dsg analyze` surfaces lots of orphaned values and gaps — good for testing proposals.

### Quick smoke test (no AI)

```bash
python3 -c "
from ds_guardian.core.rules import RulesParser
from ds_guardian.core.substitutor import CSSSubstitutor

rules = RulesParser('test_fixture/design_system.css').parse()
sub = CSSSubstitutor(rules)
css = open('test_fixture/src/card.css').read()
result = sub.substitute(css)
print(f'Script substitutions: {result.substitution_count}')
print(f'Ambiguous (needs AI): {len(result.ambiguous)}')
print(result.css[:600])
"
```

### Full commands

```bash
# Refactor
dsg start test_fixture/src --rules test_fixture/design_system.css

# Extract (generates a new design_system.css)
dsg extract test_fixture/src

# Analyze (health report + proposals)
dsg analyze test_fixture/src --rules test_fixture/design_system.css
```

---

## Known things to watch for during testing

- `RulesParser.get_token_count()` — ✅ verified exists (`core/rules.py:54`)
- `SplashScreen.show(duration, background_task)` — ✅ verified matches signature (`ui/splash.py:61`)
- `extract_workflow.py` previously took a `model` string arg; now takes `model_config` — update any call sites in tests if they exist
