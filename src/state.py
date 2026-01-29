"""Cross-day anti-repeat state management."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from .dedupe import normalize_title

_STATE_DAYS = 5


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def title_hash(title: str) -> str:
    normalized = normalize_title(title)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_history(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    history = data.get("history", [])
    if not isinstance(history, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        h = item.get("hash")
        d = item.get("date")
        if isinstance(h, str) and isinstance(d, str) and _parse_date(d):
            cleaned.append({"hash": h, "date": d})
    return cleaned


def _prune_history(history: Iterable[dict[str, str]], as_of: date) -> list[dict[str, str]]:
    cutoff = as_of - timedelta(days=_STATE_DAYS - 1)
    pruned: list[dict[str, str]] = []
    for item in history:
        d = _parse_date(item["date"])
        if d is None:
            continue
        if d >= cutoff:
            pruned.append(item)
    return pruned


def filter_items_against_history(
    items: list[dict[str, Any]],
    history: list[dict[str, str]],
    as_of: date,
) -> list[dict[str, Any]]:
    recent = _prune_history(history, as_of)
    recent_hashes = {item["hash"] for item in recent}
    filtered: list[dict[str, Any]] = []
    for item in items:
        h = title_hash(item["title"])
        if h in recent_hashes:
            continue
        filtered.append(item)
    return filtered


def update_state_file(
    path: Path,
    items: list[dict[str, Any]],
    as_of: date,
) -> None:
    history = load_history(path)
    combined: dict[str, str] = {item["hash"]: item["date"] for item in history}
    today = as_of.strftime("%Y-%m-%d")
    for item in items:
        combined[title_hash(item["title"])] = today
    merged = [{"hash": h, "date": d} for h, d in combined.items()]
    pruned = _prune_history(merged, as_of)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"history": pruned}, indent=2), encoding="utf-8")
