# NewsDiet

A small, automated daily news digest that delivers a fixed number of headlines per category in a calm, predictable format.

## Motivation

I wanted a way to stay informed without falling into endless news scrolling. This project grew out of my need for a small, automated system that delivers only the most relevant headlines in a calm, predictable format. Building it also gave me a practical way to combine software engineering fundamentals with AI tooling and to practice and get accustomed to working with AI in the CLI (Codex in this case).

## What It Does

- Fetches RSS feeds defined in `sources.yaml`.
- Normalizes and sanitizes items (removes HTML from titles/teasers).
- Optionally filters a keyword-based category using `keywords.local.yaml`.
- Deduplicates within a run and across the last 5 days.
- Selects a fixed number of items per category.
- Sends the digest to Telegram (default behavior).
- Optionally writes a Markdown file for archiving.

## Repository Structure

```
NewsDiet/
├─ .github/workflows/schedule.yml
├─ src/
│  ├─ config.py
│  ├─ dedupe.py
│  ├─ feeds.py
│  ├─ keyword_filter.py
│  ├─ main.py
│  ├─ render_md.py
│  ├─ send_telegram.py
│  └─ state.py
├─ tests/
│  └─ test_placeholder.py
├─ keywords.local.yaml
├─ sources.yaml
├─ state.json
├─ requirements.txt
└─ README.md
```

## Requirements

- Python 3.12+

Install dependencies:

```
python -m pip install -r requirements.txt
```

## Configuration

### `sources.yaml` (committed)

Defines categories, RSS sources, and selection rules:

- `limit` — max items per category
- `fresh_hours` — prefer items newer than this window (default 36)
- `max_per_source` — cap items per source (default: `limit`)
- `require_keywords` — if true and keywords missing, select zero items

### `keywords.local.yaml` (not committed)

Contains personal keywords for keyword-based categories. This file should not be committed.

Example:

```
custom_keywords_for_eastern_switzerland:
  keywords:
    - "FC St. Gallen"
    - "Fussball"
```

## Running

### Default (Telegram only)

```
python -m src.main
```

### Telegram + Markdown

```
python -m src.main --markdown
```

### Markdown only

```
python -m src.main --markdown-only
```

### Dry run (no network)

```
python -m src.main --dry-run --markdown
```

### Load environment variables from a file

```
python -m src.main --env-file .env
```

## Environment Variables

Required for Telegram:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Optional logging control:

- `LOG_LEVEL` (e.g., `INFO`, `DEBUG`)

## Output

Markdown output is written to:

```
output/YYYY-MM-DD - Daily News Diet.md
```

If `--output` is provided, that path is used instead.

## GitHub Actions

The workflow runs on a schedule and:

- Loads `KEYWORDS_YAML` secret into `keywords.local.yaml`
- Runs the app
- Commits `state.json` back to this repo

Required GitHub secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `KEYWORDS_YAML`

## Tests

```
python -m pytest
```

## Notes

- Telegram messages are sent using HTML parse mode with safe escaping.
- Messages split automatically if they approach Telegram length limits.
- If Telegram fails, the run still completes and writes markdown (if enabled).
