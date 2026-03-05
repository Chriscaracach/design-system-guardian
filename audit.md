# DS Guardian — Code Audit

> Reviewed: all source files across `ds_guardian/` package  
> Date: 2026-03-01

---

## Summary

The project has a solid structure but accumulated several real bugs, dead code, broken features, and design gaps across multiple AI sessions. Issues are grouped by severity.

---

## 🔴 Critical Bugs

### 1. Debug `print()` statements left in production code

**File:** `ds_guardian/workflow.py` lines 159–175

`_initialize_ai()` contains raw `print(f"DEBUG: ...")` statements that pollute the terminal during the splash screen. These were clearly left over from a debugging session.

**Fix:** Remove all `print(f"DEBUG: ...")` lines from `_initialize_ai()`.

---

### 2. `rules.md` token parsing is silently broken for fenced code blocks

**File:** `ds_guardian/core/rules.py` — `RulesParser.parse()`

The actual `rules.md` file wraps all token definitions inside fenced code blocks (` ``` `). The parser only looks for lines matching `^(--)?([\w-]+):\s*(.+)$` but never strips the ` ``` ` fence markers. As a result, **zero tokens are parsed** from the real `rules.md` — the tool runs but the AI receives an empty design tokens context.

**Fix:** In the parse loop, skip lines that are exactly ` ``` ` (opening/closing fences) or are inside a code fence block.

````python
# Add a fence-tracking flag
in_code_fence = False
for line in lines:
    line = line.strip()
    if line == '```':
        in_code_fence = not in_code_fence
        continue
    if in_code_fence:
        # parse token here
````

---

### 3. `--workers` flag is accepted but never used

**Files:** `ds_guardian/cli.py`, `ds_guardian/workflow.py`

`max_workers` is accepted as a constructor parameter and stored as `self.max_workers`, but `_process_all_files()` runs a plain sequential `for` loop. There is no threading/parallelism anywhere in the processing path. The flag is a no-op.

**Fix:** Either implement `concurrent.futures.ThreadPoolExecutor` with `max_workers`, or remove the flag and parameter to avoid misleading users.

---

### 4. `--no-gifs` and `--ascii-only` flags are completely ignored

**Files:** `ds_guardian/cli.py`, `ds_guardian/workflow.py`, `ds_guardian/ui/splash.py`

Both flags are parsed in the CLI but never passed to `RefactoringWorkflow` and never consulted anywhere in the code. `SplashScreen` always tries PIL/ASCII regardless.

**Fix:** Pass both flags into `RefactoringWorkflow.__init__()`, then into `SplashScreen`, and use them to gate the `_load_image()` and ASCII art paths.

---

### 5. `pager.py` uses Unix-only `tty`/`termios` — crashes on Windows

**File:** `ds_guardian/ui/pager.py` lines 13–14

```python
import tty
import termios
```

These modules are POSIX-only. Any Windows user gets an `ImportError` at startup. The project claims to support Linux/macOS but the `checker.py` says "Operating System: {os_name}" and passes it as a success for any OS.

**Fix:** Wrap the import in a try/except and provide a fallback `input()`-based character reader, or document Windows as unsupported in `README.md` and add a guard in `SetupChecker.check_os()`.

---

## 🟠 Significant Gaps

### 6. `dsg review` command is referenced but does not exist

**File:** `ds_guardian/workflow.py` line 126

```python
self.console.print(f"[yellow]Session saved. Resume with: dsg review[/yellow]")
```

The `cli.py` only registers `start` and `check-setup`. There is no `review` subcommand. A user who quits mid-session is told to run a command that will fail.

**Fix:** Either implement `dsg review` (load session, re-enter `InteractiveReviewer`), or change the message to instruct re-running `dsg start` and resuming from the saved session.

---

### 7. Session resume logic is never triggered

**File:** `ds_guardian/workflow.py` — `run()`

`RefactoringSession.load()` exists and is fully implemented, but `run()` always creates a fresh `RefactoringSession()` and re-processes all files. If a session file already exists (e.g., from a previous interrupted run), it is silently overwritten.

**Fix:** At the start of `run()`, check `self.session.exists()` — if a session file is present, prompt the user to resume it or start fresh.

---

### 8. `_process_all_files` returns `False` when no changes are found — treated as a fatal error

**File:** `ds_guardian/workflow.py` lines 232–233

```python
if len(self.session.changes) == 0:
    return False
```

`background_processing()` returns `False`, causing the splash to report "Initialization failed during splash screen" with no helpful message. The real situation (no replaceable tokens found) is perfectly normal and should be a graceful exit with a clear message.

**Fix:** Return a distinct sentinel (e.g., `'no_changes'`) or check the change count after the splash and print a friendly "No refactorable values found" message instead of a failure.

---

### 9. `SetupChecker.check_model()` always checks for `llama3.2:3b`, ignoring `--model`

**File:** `ds_guardian/checker.py` lines 126–149

The checker is hardcoded to look for `"llama3.2"` + `"3b"` regardless of what model the user is actually using (default is now `qwen2.5-coder:0.5b`). A user with only `qwen2.5-coder` installed will always see a failure.

Also: `generate_fix_commands()` line 265 tells the user to pull `llama3.2:3b`, which contradicts the actual default model.

**Fix:** Accept `model` as a parameter to `SetupChecker`, check for that specific model, and generate the correct `ollama pull` command.

---

### 10. `backup_path.relative_to(Path.cwd())` can raise in `_apply_changes`

**File:** `ds_guardian/workflow.py` line 283

```python
self.console.print(f"  [dim]Backup: {result.backup_path.relative_to(Path.cwd())}[/dim]")
```

If the target directory is outside `cwd()`, this raises `ValueError`. The backup path is constructed relative to `Path.cwd()` in `FileWriter._create_backup()`, so the paths should normally match — but if `cwd()` changes between calls, it will break.

**Fix:** Wrap in a try/except and fall back to printing the absolute path.

---

### 11. `_clean_response()` only handles the first code fence block

**File:** `ds_guardian/ai/refactorer.py` lines 226–234

````python
if "```css" in response:
    response = response.split("```css")[1].split("```")[0]
elif "```" in response:
    response = response.split("```")[1].split("```")[0]
````

If the AI returns multiple code fences (common with some models), only the first is extracted. Everything after the second fence is silently dropped, potentially returning truncated CSS.

**Fix:** Use a regex to extract the largest/last code block, or strip all fence markers in a loop.

---

### 12. `refactor_batch()` is implemented but never called

**File:** `ds_guardian/ai/refactorer.py` lines 95–144

`CSSRefactorer.refactor_batch()` is a complete implementation for multi-file batch processing, but `_process_all_files()` in `workflow.py` only calls the single-file `refactor()`. The batch method and its complex `_parse_batch_response()` are dead code.

**Fix:** Either use it (wire `_process_all_files` to batch files) or delete it to reduce maintenance surface. If the intent was to use it with `--workers`, this ties back to issue #3.

---

## 🟡 Quality / Maintainability Issues

### 13. `workflow.py` silently swallows all errors during background processing

**File:** `ds_guardian/workflow.py` lines 66–92

The `background_processing()` closure has a bare `except Exception: return False` that discards the actual exception. The outer wrapper also has the same pattern. Failures produce "Initialization failed" with no cause.

**Fix:** At minimum, store the exception and surface it after the splash clears, the same way `splash.py` does with `error[0]`.

---

### 14. `rules.md` tokens inside `## Z-Index Scale`, `## Transitions`, `## Opacity Scale` are never parsed into a named category

**File:** `ds_guardian/core/rules.py` — `CATEGORY_KEYWORDS`

The parser maps section headers to categories (`color`, `spacing`, etc.), but `z-index`, `transition`, and `opacity` have no entries in `CATEGORY_KEYWORDS`. Tokens under those headers are silently stored in `rules.custom` under their section name, but the `PromptOptimizer.filter_relevant_tokens()` always copies `custom` verbatim without filtering. This means those token groups bypass the optimizer entirely.

**Fix:** Add `'transition'`, `'z-index'`, and `'opacity'` to `CATEGORY_KEYWORDS`, or document that custom tokens are always included.

---

### 15. `SideBySideDiff` fixed 60-char column width ignores terminal width

**File:** `ds_guardian/ui/side_by_side.py` line 66

```python
left_display = left[:60].ljust(60)
```

The column is hardcoded to 60 characters. On narrow terminals (< 130 cols) the right side overflows or wraps badly. On wide terminals, space is wasted.

**Fix:** Accept terminal width from `Console().width` and compute column width dynamically (e.g., `(terminal_width - 10) // 2`).

---

### 16. `InteractivePager.scroll_offset` is not reset between files

**File:** `ds_guardian/ui/pager.py` — `InteractivePager.__init__`

`scroll_offset` and `rules_scroll_offset` are set once at construction. If the same `InteractivePager` instance is reused across files (it is — it's created in `InteractiveReviewer.__init__`), the scroll position carries over from the previous file.

**Fix:** Reset `self.scroll_offset = 0` at the start of each `show()` call.

---

### 17. `main.py` is a duplicate of `cli.py` with slight divergences

**File:** `main.py`

The root `main.py` duplicates the entire `cli.py` argument parser. The `--model` help text differs between the two files. There is no indication `main.py` is called anywhere in production. It will confuse contributors.

**Fix:** Remove `main.py` entirely, or reduce it to a one-liner: `from ds_guardian.cli import main; main()`.

---

### 18. `FileWriter._create_backup()` creates a new timestamp per file, not per session

**File:** `ds_guardian/core/writer.py` line 108

```python
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
```

If `_apply_changes()` writes multiple files sequentially and the clock ticks over a second boundary, backups land in different subdirectories. `list_backups()` then treats them as separate sessions.

**Fix:** Generate the timestamp once in `FileWriter.__init__()` (or pass it as a session ID), and reuse it for all writes in a single apply pass.

---

### 19. No error feedback when `rules.md` is missing at startup

**File:** `ds_guardian/workflow.py` — `_load_rules()`

```python
except Exception:
    return False
```

If `rules.md` doesn't exist, `FileNotFoundError` is caught silently and the tool fails with the generic "Initialization failed" splash message. The user has no idea what went wrong.

**Fix:** Catch `FileNotFoundError` specifically and surface a clear message: `"Rules file not found: rules.md — pass --rules <path> to specify a different file."`.

---

### 20. `PromptOptimizer._is_color_relevant` double-checks the same condition

**File:** `ds_guardian/ai/optimizer.py` lines 119–133

The method checks `token_lower in css_colors` and then loops over `css_colors` checking `css_color.lower() == token_lower`. These are logically equivalent — the second loop adds no new cases.

**Fix:** Remove the redundant loop; keep only the `in` membership test.

---

## 🔵 Missing Features (Promised but Absent)

| Feature                             | Where referenced                | Status                   |
| ----------------------------------- | ------------------------------- | ------------------------ |
| `dsg review` command                | `workflow.py:126`               | Not implemented          |
| Parallel `--workers`                | `cli.py`, `workflow.py`         | Wired to nothing         |
| Session resume                      | `session.py` has full load/save | Never triggered          |
| `--no-gifs` / `--ascii-only`        | `cli.py`                        | Flags accepted, ignored  |
| Model validation in `--check-setup` | `checker.py`                    | Hardcoded to wrong model |

---

## Recommended Fix Order

1. **#2** — Fix token parsing (fenced code blocks) — without this, the tool does nothing useful
2. **#1** — Remove debug prints
3. **#8** — Graceful "no changes found" exit
4. **#9** — Fix `check_model()` to use the configured model
5. **#6 + #7** — Implement `dsg review` / session resume
6. **#3** — Implement or remove `--workers`
7. **#4** — Wire `--no-gifs` / `--ascii-only` through
8. **#16** — Reset pager scroll between files
9. **#18** — Fix backup timestamp per session
10. **#17** — Remove/simplify `main.py`
11. Remaining quality issues as time allows
