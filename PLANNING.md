# Daily News Diet – Configuration

This document describes how configuration is handled to support a **public repository** while keeping **personal keywords private**.

---

## sources.yaml (committed)

Defines:
- Categories
- RSS feed URLs
- Per-category limits
- Optional default (non-personal) keyword lists

This file **is committed to git** and provides a reproducible baseline configuration.

### Example

```yaml
categories:
  world:
    limit: 3
    sources:
      - type: rss
        url: https://example.com/world.rss

  germany_europe:
    limit: 5
    sources:
      - type: rss
        url: https://example.com/europe.rss

  custom_ch:
    limit: 3
```
---

## keywords.local.yaml (not committed)

Defines:
- Personal keyword lists for filtering (e.g. work- or location-specific terms)

This file **must NOT be committed to git**, as it may contain personal or sensitive keywords.
It is listed in `.gitignore`.

### Runtime behavior
At runtime, the application should:

1. Load `sources.yaml`
2. If `keywords.local.yaml` exists, merge its keyword lists into the relevant categories (e.g. `custom_ch`)
3. Proceed with filtering using the merged configuration

### Example

```yaml
custom_ch:
  keywords:
    - peregrina
    - asyl
    - thurgau
    - staatssekretariat für migration
    - sem
```

---

## GitHub Actions setup

For automated runs:

- Store the contents of `keywords.local.yaml` in a GitHub repository secret  
  (e.g. `KEYWORDS_YAML`)
- During the workflow, write the secret to disk before running the app

This keeps the repository public while ensuring personal keywords are never exposed.

---

## Design principles

- Configuration is treated as code where possible
- Personal data is explicitly separated and excluded from version control
- The system must work even if `keywords.local.yaml` is missing

---

End of document.
