"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import logging

import yaml

_LOGGER = logging.getLogger(__name__)

def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a mapping at the top level")
    return data


def _warn_invalid(category: str, reason: str) -> None:
    _LOGGER.warning("Skipping category '%s': %s", category, reason)


def load_config(sources_path: Path, keywords_path: Path | None = None) -> dict[str, Any]:
    raw = _load_yaml(sources_path)
    categories = raw.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("sources.yaml must contain a 'categories' mapping")

    config: dict[str, Any] = {"categories": {}}
    for key, value in categories.items():
        if not isinstance(value, dict):
            _warn_invalid(key, "category entry must be a mapping")
            continue
        limit = value.get("limit")
        fresh_hours = value.get("fresh_hours", 36)
        max_per_source = value.get("max_per_source", limit)
        require_keywords = value.get("require_keywords", False)
        sources = value.get("sources")
        if not isinstance(limit, int) or not isinstance(sources, list):
            _warn_invalid(key, "missing or invalid 'limit' or 'sources'")
            continue
        if not isinstance(fresh_hours, int) or fresh_hours <= 0:
            _warn_invalid(key, "invalid 'fresh_hours' (must be positive int)")
            continue
        if not isinstance(max_per_source, int) or max_per_source <= 0:
            _warn_invalid(key, "invalid 'max_per_source' (must be positive int)")
            continue
        if not isinstance(require_keywords, bool):
            _warn_invalid(key, "invalid 'require_keywords' (must be boolean)")
            continue
        valid_sources = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            if source.get("type") != "rss":
                continue
            url = source.get("url")
            if not isinstance(url, str) or not url:
                continue
            valid_sources.append(source)
        if not valid_sources:
            _warn_invalid(key, "no valid RSS sources found")
            continue
        config["categories"][key] = {
            "limit": limit,
            "fresh_hours": fresh_hours,
            "max_per_source": max_per_source,
            "require_keywords": require_keywords,
            "sources": valid_sources,
            "keywords": [],
        }

    if not config["categories"]:
        raise ValueError("sources.yaml contains no valid categories")

    if keywords_path and keywords_path.exists():
        try:
            keywords_raw = _load_yaml(keywords_path)
        except ValueError as exc:
            _LOGGER.warning("Ignoring keywords file: %s", exc)
            return config
        for key, value in keywords_raw.items():
            if key not in config["categories"]:
                _LOGGER.warning("Keywords provided for unknown category '%s'", key)
                continue
            if not isinstance(value, dict):
                _LOGGER.warning("Invalid keywords entry for '%s'", key)
                continue
            keywords = value.get("keywords")
            if isinstance(keywords, list):
                config["categories"][key]["keywords"] = [
                    kw for kw in keywords if isinstance(kw, str)
                ]
            else:
                _LOGGER.warning("Invalid keywords list for '%s'", key)

    return config
