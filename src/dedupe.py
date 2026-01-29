"""Title normalization and same-day deduplication."""

from __future__ import annotations

import re
import string
from datetime import datetime
from typing import Any

_PUNCTUATION_TABLE = str.maketrans({ch: " " for ch in string.punctuation})


def normalize_title(title: str) -> str:
    cleaned = title.lower().translate(_PUNCTUATION_TABLE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _is_newer(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_dt = left.get("published")
    right_dt = right.get("published")
    if isinstance(left_dt, datetime) and isinstance(right_dt, datetime):
        return left_dt > right_dt
    if isinstance(left_dt, datetime):
        return True
    if isinstance(right_dt, datetime):
        return False
    return False


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        key = normalize_title(item.get("title", ""))
        if not key:
            continue
        existing = deduped.get(key)
        if existing is None or _is_newer(item, existing):
            deduped[key] = item
    return list(deduped.values())
