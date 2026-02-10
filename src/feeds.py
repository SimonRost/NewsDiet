"""RSS feed ingestion and normalization."""

from __future__ import annotations

import calendar
import html
import logging
import re
from datetime import datetime, timezone
from typing import Any

import feedparser

_TAG_RE = re.compile(r"<[^>]+>")
_LOGGER = logging.getLogger(__name__)


def _strip_html(value: str) -> str:
    if not value:
        return ""
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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
    title = _strip_html((entry.get("title") or "").strip())
    teaser = _strip_html((entry.get("summary") or entry.get("description") or "").strip())
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


def fetch_category_items(
    category: str, cfg: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    items: list[dict[str, Any]] = []
    stats = {"feeds_total": 0, "feeds_ok": 0, "feeds_failed": 0}
    sources = cfg.get("sources", [])
    valid_sources = [s for s in sources if isinstance(s, dict) and s.get("type") == "rss"]
    if not valid_sources:
        _LOGGER.warning("No valid sources for category '%s', skipping.", category)
        return items, stats

    for source in valid_sources:
        stats["feeds_total"] += 1
        url = source.get("url")
        if not isinstance(url, str) or not url:
            stats["feeds_failed"] += 1
            _LOGGER.warning("Invalid feed URL for category '%s'.", category)
            continue
        name = source.get("name") if isinstance(source.get("name"), str) else None
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:
            stats["feeds_failed"] += 1
            _LOGGER.warning("Failed to fetch feed '%s': %s", url, exc)
            continue
        stats["feeds_ok"] += 1
        for entry in parsed.entries:
            normalized = _normalize_entry(entry, name, category)
            if normalized["title"] and normalized["link"]:
                items.append(normalized)
    return items, stats
