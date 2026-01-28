# Daily News Diet — PLANNING.md

Planning document and product specification for the **Daily News Diet** project.

---

## 1. Project Overview

### Goal
Create an automated daily news digest that delivers a **fixed, limited number of headlines** across predefined categories.

The system must:
- avoid infinite scroll
- minimize temptation
- be reliable without manual intervention
- work in a public repository while keeping personal data private

### Core idea
Bounded news consumption by design. You get the news **once per day**, in a finite list, then you’re done.

---

## 2. Outputs (per daily run)

### 2.1 Telegram Message
- Delivered via Telegram bot
- Structured by category
- Each item contains:
  - Headline
  - Short teaser (from RSS)
  - Link to full article

### 2.2 Markdown File (Obsidian)
- One file per day
- Filename: `YYYY-MM-DD - Daily News Diet.md`
- Stored in a dedicated folder inside the Obsidian vault repo
- Same content as Telegram, formatted for long-term reading/archival

---

## 3. Scheduling & Delivery

- **Execution environment:** GitHub Actions
- **Trigger:** scheduled daily run
- **Why:** runs even if local machine is asleep; low maintenance

### Secrets (not committed)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- (optional) `KEYWORDS_YAML`

### Markdown sync strategy
- GitHub Action commits the generated `.md` file directly into the private Obsidian vault repository
- Local Mac pulls changes via automated `git pull` (handled outside this project)

---

## 4. News Categories & Rules

### Category 1: World News
- **Limit:** Top 3 items
- **Language:** English or German
- **Source type:** RSS
- **Examples:**
  - Spiegel International
  - Süddeutsche Zeitung International

**Selection logic:**
- Merge feeds
- Deduplicate by normalized title
- Sort by publication date
- Take first 3

---

### Category 2: Germany & Europe
- **Limit:** Top 5 items
- **Language:** German
- **Source type:** RSS
- **Examples:**
  - Spiegel Politik / Europa
  - Die Zeit Politik

**Selection logic:** same as Category 1

---

### Category 3: Switzerland
- **Limit:** Top 3 items
- **Language:** German
- **Source type:** RSS
- **Examples:**
  - NZZ Schweiz
  - SRF News Schweiz

**Selection logic:** same as Category 1

---

### Category 4: Custom Local / Work-Related (Eastern Switzerland)
- **Limit:** Top 3 items
- **Primary source:**
  - Tagblatt RSS feeds (local sections)

**Filtering:**
- Keyword scan on RSS title + teaser
- Case-insensitive

**Optional widening:**
- Google News RSS queries restricted to Switzerland or specific domains

**Selection logic:**
- Keep only keyword matches
- Deduplicate
- Sort by date
- Take first 3

---

### Anti-repeat rule (cross-day)

**Goal:**  
Avoid sending the same headline on consecutive days (frontpages often repeat for 2–3 days).

**Mechanism:**
- Persist a history of sent headlines for the last **5 days**
- Filter new candidates against this history before final selection

**Implementation notes:**
- Store normalized title hashes with sent date in a small state file (JSON)
- State file is committed by GitHub Actions so history persists across runs

**Fallback behavior:**
- If filtering removes too many items, continue down the feed list until the per-category limit is met (best-effort)

---

## 5. Technical Stack

### Language & Runtime
- Python 3.12+

### Libraries
- `feedparser` — RSS ingestion
- `requests` — Telegram Bot API
- Standard library:
  - `datetime`
  - `pathlib`
  - `hashlib`
  - `json`

### Formatting
- Plain Markdown generation
- Telegram Markdown (no HTML)

---

## 6. Configuration

### sources.yaml (committed)
Defines:
- Categories
- RSS feed URLs
- Per-category limits
- No personal data

Example:
```yaml
categories:
  world:
    limit: 3
    sources:
      - type: rss
        url: https://example.com/world.rss

  custom_ch:
    limit: 3
```

---

### keywords.local.yaml (NOT committed)
Defines:
- Personal keyword lists for filtering

Rules:
- Must be listed in `.gitignore`
- Loaded at runtime if present
- Merged into the configuration
- For GitHub Actions, provided via a secret (`KEYWORDS_YAML`) and written to disk during the workflow

---

## 7. Repository Structure (current)

Based on the current project state:

```text
NewsDiet/
├─ .github/
│  └─ workflows/
│     └─ schedule.yml
├─ src/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ dedupe.py
│  ├─ feeds.py
│  ├─ keyword_filter.py
│  ├─ main.py
│  ├─ render_md.py
│  └─ send_telegram.py
├─ tests/
│  ├─ __init__.py
│  └─ test_placeholder.py
├─ .gitignore
├─ AGENTS.md
├─ LICENSE
├─ PLANNING.md
├─ README.md
├─ requirements.txt
└─ sources.yaml
```

---

## 8. Non-goals (explicit)

- No UI
- No mobile app
- No social media sources
- No infinite feeds or pagination
- No personalization or recommendation algorithms
- No LLM-based summarization

---

## 9. Success Criteria

- Digest arrives daily without manual intervention
- Total daily items ≤ 14
- Reading time < 5 minutes
- No repeated headlines across consecutive days
- No built-in path to endless consumption

---

End of document.
