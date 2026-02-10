"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("sources.yaml must contain a mapping at the top level")
    return data


def load_config(sources_path: Path, keywords_path: Path | None = None) -> dict[str, Any]:
    raw = _load_yaml(sources_path)
    categories = raw.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("sources.yaml must contain a 'categories' mapping")

    config: dict[str, Any] = {"categories": {}}
    for key, value in categories.items():
        if not isinstance(value, dict):
            continue
        limit = value.get("limit")
        fresh_hours = value.get("fresh_hours", 36)
        max_per_source = value.get("max_per_source", limit)
        sources = value.get("sources")
        if not isinstance(limit, int) or not isinstance(sources, list):
            continue
        if not isinstance(fresh_hours, int) or fresh_hours <= 0:
            continue
        if not isinstance(max_per_source, int) or max_per_source <= 0:
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
        config["categories"][key] = {
            "limit": limit,
            "fresh_hours": fresh_hours,
            "max_per_source": max_per_source,
            "sources": valid_sources,
            "keywords": [],
        }

    if keywords_path and keywords_path.exists():
        keywords_raw = _load_yaml(keywords_path)
        for key, value in keywords_raw.items():
            if key not in config["categories"]:
                continue
            if not isinstance(value, dict):
                continue
            keywords = value.get("keywords")
            if isinstance(keywords, list):
                config["categories"][key]["keywords"] = [
                    kw for kw in keywords if isinstance(kw, str)
                ]

    return config
