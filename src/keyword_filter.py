"""Keyword and category filtering."""

from __future__ import annotations

from typing import Any


def filter_by_keywords(
    items: list[dict[str, Any]],
    keywords: list[str],
) -> list[dict[str, Any]]:
    if not keywords:
        return items
    lowered = [kw.lower() for kw in keywords]
    filtered: list[dict[str, Any]] = []
    for item in items:
        haystack = f"{item.get('title', '')} {item.get('teaser', '')}".lower()
        if any(kw in haystack for kw in lowered):
            filtered.append(item)
    return filtered
