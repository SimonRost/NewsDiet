"""App entrypoint and M1 orchestration."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import load_config
from .dedupe import dedupe_items
from .feeds import fetch_category_items
from .keyword_filter import filter_by_keywords
from .render_md import render_markdown
from .state import filter_items_against_history, load_history, update_state_file


_DEFAULT_SOURCES = Path("sources.yaml")
_DEFAULT_KEYWORDS = Path("keywords.local.yaml")
_DEFAULT_OUTPUT = Path("output.md")
_DEFAULT_STATE = Path("state.json")
_DEFAULT_FIXTURES = Path("tests/fixtures/sample_items.json")


def _parse_fixture_datetime(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_fixtures(path: Path) -> dict[str, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    categories = data.get("categories", {})
    if not isinstance(categories, dict):
        raise ValueError("Fixture file must contain a 'categories' mapping")
    normalized: dict[str, list[dict[str, Any]]] = {}
    for key, items in categories.items():
        if not isinstance(items, list):
            continue
        normalized[key] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            published = item.get("published")
            published_dt = None
            if isinstance(published, str):
                published_dt = _parse_fixture_datetime(published)
            normalized[key].append(
                {
                    "title": item.get("title", ""),
                    "teaser": item.get("teaser", ""),
                    "link": item.get("link", ""),
                    "published": published_dt,
                    "source": item.get("source"),
                    "category": key,
                }
            )
    return normalized


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple[int, datetime]:
        published = item.get("published")
        if isinstance(published, datetime):
            return (0, published)
        return (1, datetime.min.replace(tzinfo=timezone.utc))

    return sorted(items, key=sort_key, reverse=True)


def build_items_by_category(
    config: dict[str, Any],
    history: list[dict[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    today = datetime.now(timezone.utc).date()
    result: dict[str, list[dict[str, Any]]] = {}
    for category, cfg in config["categories"].items():
        items = fetch_category_items(category, cfg)
        keywords = cfg.get("keywords", [])
        if keywords:
            items = filter_by_keywords(items, keywords)
        items = dedupe_items(items)
        items = _sort_items(items)
        items = filter_items_against_history(items, history, today)
        limit = cfg.get("limit", 0)
        if isinstance(limit, int) and limit > 0:
            items = items[:limit]
        result[category] = items
    return result


def build_items_from_fixtures(
    fixtures_path: Path,
    config: dict[str, Any],
    history: list[dict[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    data = _load_fixtures(fixtures_path)
    today = datetime.now(timezone.utc).date()
    result: dict[str, list[dict[str, Any]]] = {}
    for category, cfg in config["categories"].items():
        items = data.get(category, [])
        keywords = cfg.get("keywords", [])
        if keywords:
            items = filter_by_keywords(items, keywords)
        items = dedupe_items(items)
        items = _sort_items(items)
        items = filter_items_against_history(items, history, today)
        limit = cfg.get("limit", 0)
        if isinstance(limit, int) and limit > 0:
            items = items[:limit]
        result[category] = items
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="NewsDiet M1")
    parser.add_argument("--sources", default=str(_DEFAULT_SOURCES))
    parser.add_argument("--keywords", default=str(_DEFAULT_KEYWORDS))
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT))
    parser.add_argument("--state", default=str(_DEFAULT_STATE))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixtures", default=str(_DEFAULT_FIXTURES))
    args = parser.parse_args()

    sources_path = Path(args.sources)
    keywords_path = Path(args.keywords)
    output_path = Path(args.output)
    state_path = Path(args.state)
    fixtures_path = Path(args.fixtures)

    config = load_config(sources_path, keywords_path)
    history = load_history(state_path)

    if args.dry_run:
        items_by_category = build_items_from_fixtures(fixtures_path, config, history)
    else:
        items_by_category = build_items_by_category(config, history)

    today = datetime.now(timezone.utc).date()
    markdown = render_markdown(items_by_category, today)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    if not args.dry_run:
        flat_items = [item for items in items_by_category.values() for item in items]
        update_state_file(state_path, flat_items, today)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
