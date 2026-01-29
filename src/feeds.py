"""RSS feed ingestion and normalization."""

from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import Any

import feedparser


def _parse_datetime(entry: dict[str, Any]) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    try:
        timestamp = calendar.timegm(parsed)
    except (TypeError, OverflowError):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _normalize_entry(
    entry: dict[str, Any],
    source_name: str | None,
    category: str,
) -> dict[str, Any]:
    title = (entry.get("title") or "").strip()
    teaser = (entry.get("summary") or entry.get("description") or "").strip()
    link = (entry.get("link") or "").strip()
    published = _parse_datetime(entry)
    return {
        "title": title,
        "teaser": teaser,
        "link": link,
        "published": published,
        "source": source_name,
        "category": category,
    }


def fetch_category_items(category: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    sources = cfg.get("sources", [])
    valid_sources = [s for s in sources if isinstance(s, dict) and s.get("type") == "rss"]
    if not valid_sources:
        print(f"No valid sources for category '{category}', skipping.")
        return items

    for source in valid_sources:
        url = source.get("url")
        if not isinstance(url, str) or not url:
            continue
        name = source.get("name") if isinstance(source.get("name"), str) else None
        try:
            parsed = feedparser.parse(url)
        except Exception:
            print(f"Failed to fetch feed: {url}")
            continue
        for entry in parsed.entries:
            normalized = _normalize_entry(entry, name, category)
            if normalized["title"] and normalized["link"]:
                items.append(normalized)
    return items
