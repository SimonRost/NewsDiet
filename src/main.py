"""App entrypoint and M2 orchestration."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import load_config
from .dedupe import dedupe_items
from .feeds import fetch_category_items
from .keyword_filter import filter_by_keywords
from .render_md import render_markdown
from .send_telegram import send_daily_digest
from .state import filter_items_against_history, load_history, update_state_file


_DEFAULT_SOURCES = Path("sources.yaml")
_DEFAULT_KEYWORDS = Path("keywords.local.yaml")
_DEFAULT_STATE = Path("state.json")
_DEFAULT_FIXTURES = Path("tests/fixtures/sample_items.json")

_LOGGER = logging.getLogger(__name__)


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
    def sort_key(item: dict[str, Any]) -> tuple[int, float]:
        published = item.get("published")
        if isinstance(published, datetime):
            return (1, published.timestamp())
        return (0, 0.0)

    return sorted(items, key=sort_key, reverse=True)


def _default_output_path(as_of: date) -> Path:
    filename = f"{as_of.strftime('%Y-%m-%d')} - Daily News Diet.md"
    return Path("output") / filename


def _load_env_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _partition_fresh(
    items: list[dict[str, Any]], cutoff: datetime
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fresh: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    for item in items:
        published = item.get("published")
        if isinstance(published, datetime) and published >= cutoff:
            fresh.append(item)
        else:
            stale.append(item)
    return fresh, stale


def _apply_source_cap(
    items: list[dict[str, Any]],
    max_per_source: int,
    counts: dict[str, int],
    limit: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for item in items:
        if len(selected) >= limit:
            break
        source = item.get("source")
        source_key = source if isinstance(source, str) and source else "unknown"
        if counts.get(source_key, 0) >= max_per_source:
            continue
        counts[source_key] = counts.get(source_key, 0) + 1
        selected.append(item)
    return selected


def _select_items_for_category(
    items: list[dict[str, Any]],
    cfg: dict[str, Any],
    history: list[dict[str, str]],
    now: datetime,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {
        "fetched": len(items),
        "after_keyword": 0,
        "after_dedupe": 0,
        "after_anti_repeat": 0,
        "final": 0,
    }

    keywords = cfg.get("keywords", [])
    require_keywords = cfg.get("require_keywords", False)
    if require_keywords and not keywords:
        return [], stats

    if keywords:
        items = filter_by_keywords(items, keywords)
    stats["after_keyword"] = len(items)

    items = dedupe_items(items)
    stats["after_dedupe"] = len(items)

    items = _sort_items(items)

    fresh_hours = cfg.get("fresh_hours", 36)
    cutoff = now - timedelta(hours=fresh_hours)
    fresh_items, stale_items = _partition_fresh(items, cutoff)

    history_date = now.date()
    fresh_items = filter_items_against_history(fresh_items, history, history_date)
    stale_items = filter_items_against_history(stale_items, history, history_date)
    stats["after_anti_repeat"] = len(fresh_items) + len(stale_items)

    limit = cfg.get("limit", 0)
    if not isinstance(limit, int) or limit <= 0:
        return [], stats

    max_per_source = cfg.get("max_per_source", limit)
    if not isinstance(max_per_source, int) or max_per_source <= 0:
        max_per_source = limit

    counts: dict[str, int] = {}
    selected = _apply_source_cap(fresh_items, max_per_source, counts, limit)
    if len(selected) < limit:
        remaining = limit - len(selected)
        backfill = _apply_source_cap(stale_items, max_per_source, counts, remaining)
        selected.extend(backfill)

    stats["final"] = len(selected)
    return selected, stats


def build_items_by_category(
    config: dict[str, Any],
    history: list[dict[str, str]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, int]], dict[str, int]]:
    now = datetime.now(timezone.utc)
    result: dict[str, list[dict[str, Any]]] = {}
    per_category_stats: dict[str, dict[str, int]] = {}
    feed_stats = {"feeds_total": 0, "feeds_ok": 0, "feeds_failed": 0}

    for category, cfg in config["categories"].items():
        items, stats = fetch_category_items(category, cfg)
        for key in feed_stats:
            feed_stats[key] += stats.get(key, 0)
        selected, cat_stats = _select_items_for_category(items, cfg, history, now)
        result[category] = selected
        per_category_stats[category] = cat_stats

    return result, per_category_stats, feed_stats


def build_items_from_fixtures(
    fixtures_path: Path,
    config: dict[str, Any],
    history: list[dict[str, str]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, int]]]:
    data = _load_fixtures(fixtures_path)
    now = datetime.now(timezone.utc)
    result: dict[str, list[dict[str, Any]]] = {}
    per_category_stats: dict[str, dict[str, int]] = {}
    for category, cfg in config["categories"].items():
        items = data.get(category, [])
        selected, cat_stats = _select_items_for_category(items, cfg, history, now)
        result[category] = selected
        per_category_stats[category] = cat_stats
    return result, per_category_stats


def _write_markdown(items_by_category: dict[str, list[dict[str, Any]]], as_of: date, output: str) -> bool:
    try:
        output_path = Path(output) if output else _default_output_path(as_of)
        markdown = render_markdown(items_by_category, as_of)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return True
    except OSError as exc:
        _LOGGER.warning("Failed to write markdown: %s", exc)
        return False


def _configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    _configure_logging()

    parser = argparse.ArgumentParser(description="NewsDiet M2")
    parser.add_argument("--sources", default=str(_DEFAULT_SOURCES))
    parser.add_argument("--keywords", default=str(_DEFAULT_KEYWORDS))
    parser.add_argument("--output", default="")
    parser.add_argument("--state", default=str(_DEFAULT_STATE))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixtures", default=str(_DEFAULT_FIXTURES))
    parser.add_argument("--env-file", default="")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--markdown-only", action="store_true")
    args = parser.parse_args()

    if args.env_file:
        _load_env_file(Path(args.env_file))

    sources_path = Path(args.sources)
    keywords_path = Path(args.keywords)
    state_path = Path(args.state)
    fixtures_path = Path(args.fixtures)

    try:
        config = load_config(sources_path, keywords_path)
    except ValueError as exc:
        _LOGGER.error("Config error: %s", exc)
        return 1

    history = load_history(state_path)

    feed_stats = {"feeds_total": 0, "feeds_ok": 0, "feeds_failed": 0}
    if args.dry_run:
        items_by_category, per_category_stats = build_items_from_fixtures(
            fixtures_path, config, history
        )
    else:
        items_by_category, per_category_stats, feed_stats = build_items_by_category(
            config, history
        )

    today = datetime.now(timezone.utc).date()

    markdown_written = False
    if args.markdown or args.markdown_only:
        markdown_written = _write_markdown(items_by_category, today, args.output)

    telegram_sent = False
    if not args.dry_run and not args.markdown_only:
        telegram_sent = send_daily_digest(items_by_category, today)

    if not args.dry_run:
        flat_items = [item for items in items_by_category.values() for item in items]
        update_state_file(state_path, flat_items, today)

    _LOGGER.info("Run summary")
    for category, stats in per_category_stats.items():
        _LOGGER.info(
            "Category '%s': fetched=%s after_keyword=%s after_dedupe=%s after_anti_repeat=%s final=%s",
            category,
            stats.get("fetched"),
            stats.get("after_keyword"),
            stats.get("after_dedupe"),
            stats.get("after_anti_repeat"),
            stats.get("final"),
        )
    _LOGGER.info(
        "Feeds: total=%s ok=%s failed=%s",
        feed_stats.get("feeds_total"),
        feed_stats.get("feeds_ok"),
        feed_stats.get("feeds_failed"),
    )
    _LOGGER.info("Telegram sent=%s", telegram_sent)
    _LOGGER.info("Markdown written=%s", markdown_written)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
