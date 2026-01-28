# Repository Guidelines

## Project Structure & Module Organization
- Current repo contains a minimal scaffold: `src/`, `tests/`, `sources.yaml`, `requirements.txt`, `README.md`, and a GitHub Actions workflow under `.github/workflows/`.
- Application code lives under `src/`, tests under `tests/`, and configuration in `sources.yaml` at the repository root.
- Avoid checking in local IDE artifacts (`.idea/`) or virtualenvs (`.venv/`) once code exists; keep them ignored by Git.

## Build, Test, and Development Commands
- Tests run with `python -m pytest`.
- If a virtual environment is required, standardize on `python -m venv .venv` and note activation steps in this section.
- The main configuration file will be `sources.yaml`.

## Coding Style & Naming Conventions
- Language target is Python 3.12+ per `PLANNING.md`. Use 4-space indentation and type hints for public APIs.
- Prefer lowercase module names (`rss_ingest.py`), and use `snake_case` for functions/variables.
- If a formatter/linter is introduced (e.g., `ruff`, `black`), add the exact commands and config file paths here.

## Testing Guidelines
- No testing framework is configured yet. When tests are added, prefer `pytest` and locate tests under `tests/` with filenames like `test_<module>.py`.
- Use `pytest` as the standard test runner.
- State coverage expectations explicitly once they exist.

## Commit & Pull Request Guidelines
- There is no commit history yet. Use a clear, consistent convention such as Conventional Commits (`feat:`, `fix:`, `chore:`) until a project-specific standard is established.
- PRs should include a concise description, manual test notes (if applicable), and any relevant screenshots or logs.

## Mandatory Pre-Step (Before Any Code Changes)

Before writing, editing, or deleting any code, the agent MUST:

1. List every file that will be created or modified.
2. Explain, in 1–2 sentences per file, why each change is necessary.
3. Wait for explicit user approval before applying changes.

If this step is skipped, the changes should be considered invalid and must be redone.

## Agent-Specific Instructions
- Keep updates consistent with the goals in `PLANNING.md` (bounded daily digest, Telegram + Markdown output, scheduled execution).
- If you add new top-level files or directories, update this guide to reflect the structure and commands.

## Agent Rules (NewsDiet MVP)
- Prime directive: ship a working MVP fast with minimal complexity. Prefer boring, readable code over cleverness.
- Scope control: implement only the current milestone. No UI. No summarization/LLMs. No scraping unless RSS is impossible.
- Architecture: keep it small (max ~6–8 modules under `src/`). Prefer functions and `dataclasses` over classes unless they clearly simplify.
- Dependencies: prefer stdlib. Allowed (initially): `feedparser`, `requests`, `pyyaml` (config). Avoid heavy frameworks.
- Secrets: never commit secrets. Read from env vars only: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Outputs: Telegram + Markdown must include category headings and, per item, headline + teaser + link. Respect per-category limits.
- Reliability: if one feed fails, continue; if Telegram fails, still write Markdown. Never crash on one malformed item.
- Deduplication: dedupe by normalized title (lowercase, collapse whitespace, basic punctuation stripping). Keep newest.
- Keyword filtering (Category 4): match keywords against `title + teaser` case-insensitively. Simple OR logic only.
- Tests (pytest): at minimum test title normalization/dedupe and keyword matching. No network calls in tests.
- GitHub Actions: scheduled daily run, install deps, run app, commit new Markdown via `GITHUB_TOKEN`. Never print secrets.

## Working With Codex (Suggested Workflow)
1. Keep tasks tiny: one change at a time (e.g., “create sources.yaml parser”, then “render Markdown”, then “send Telegram”).
2. Always ask for a plan first: have Codex list which files it will add/modify and the exact commands to run.
3. Review diffs before approval: use `/review` and scan for scope creep, extra dependencies, and secret handling.
4. Run locally after each step:
   - `python -m pytest`
   - a “dry run” command that does not send Telegram (or uses a flag/env to skip sending) (Support DRY_RUN=1 to skip Telegram sending.)
5. Commit in small chunks with clear messages (e.g., `feat: add rss ingest`, `test: add dedupe tests`).
6. Only after local success, enable/adjust the GitHub Actions schedule.

## Milestones
- M0 (Scaffold): `src/` + `tests/` + `sources.yaml` + basic README + minimal workflow file.
- M1 (Core logic): fetch RSS → filter/keywords → dedupe → render Markdown.
- M2 (Delivery): send Telegram + write Markdown into vault path.
- M3 (Automation): GitHub Actions schedule + commit/push Markdown.
