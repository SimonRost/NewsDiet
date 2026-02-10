from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.dedupe import dedupe_items, normalize_title
from src.keyword_filter import filter_by_keywords
from src.main import _select_items_for_category
from src.state import filter_items_against_history, title_hash, update_state_file


def test_normalize_title_and_dedupe_keeps_newest() -> None:
    title_a = "Hello,   World!"
    title_b = "Hello World"
    assert normalize_title(title_a) == "hello world"

    items = [
        {
            "title": title_a,
            "teaser": "",
            "link": "https://example.com/a",
            "published": datetime(2025, 1, 1, tzinfo=timezone.utc),
        },
        {
            "title": title_b,
            "teaser": "",
            "link": "https://example.com/b",
            "published": datetime(2025, 1, 2, tzinfo=timezone.utc),
        },
    ]
    deduped = dedupe_items(items)
    assert len(deduped) == 1
    assert deduped[0]["link"] == "https://example.com/b"


def test_keyword_filtering_case_insensitive() -> None:
    items = [
        {"title": "Peregrina opens center", "teaser": "", "link": "x"},
        {"title": "Other news", "teaser": "Asyl topic", "link": "y"},
        {"title": "Unrelated", "teaser": "", "link": "z"},
    ]
    keywords = ["peregrina", "asyl"]
    filtered = filter_by_keywords(items, keywords)
    assert [item["link"] for item in filtered] == ["x", "y"]


def test_cross_day_anti_repeat(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    as_of = date(2025, 1, 10)
    items = [
        {
            "title": "Repeated headline",
            "teaser": "",
            "link": "https://example.com/1",
            "published": datetime(2025, 1, 10, tzinfo=timezone.utc),
        }
    ]
    update_state_file(state_path, items, as_of)

    history = [
        {
            "hash": title_hash("Repeated headline"),
            "date": "2025-01-10",
        }
    ]
    filtered = filter_items_against_history(items, history, as_of)
    assert filtered == []


def test_fresh_window_with_backfill() -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    items = [
        {
            "title": "Fresh item",
            "teaser": "",
            "link": "https://example.com/fresh",
            "published": now - timedelta(hours=2),
            "source": "a",
        },
        {
            "title": "Old item",
            "teaser": "",
            "link": "https://example.com/old",
            "published": now - timedelta(hours=50),
            "source": "b",
        },
        {
            "title": "No date item",
            "teaser": "",
            "link": "https://example.com/nodate",
            "published": None,
            "source": "c",
        },
    ]
    cfg = {"limit": 2, "fresh_hours": 24, "max_per_source": 2, "keywords": []}
    selected = _select_items_for_category(items, cfg, [], now)
    assert [item["link"] for item in selected] == [
        "https://example.com/fresh",
        "https://example.com/old",
    ]


def test_per_source_cap_fills_from_others() -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    items = [
        {
            "title": "A1",
            "teaser": "",
            "link": "https://example.com/a1",
            "published": now - timedelta(hours=1),
            "source": "a",
        },
        {
            "title": "A2",
            "teaser": "",
            "link": "https://example.com/a2",
            "published": now - timedelta(hours=2),
            "source": "a",
        },
        {
            "title": "B1",
            "teaser": "",
            "link": "https://example.com/b1",
            "published": now - timedelta(hours=3),
            "source": "b",
        },
        {
            "title": "C1",
            "teaser": "",
            "link": "https://example.com/c1",
            "published": now - timedelta(hours=4),
            "source": "c",
        },
    ]
    cfg = {"limit": 3, "fresh_hours": 36, "max_per_source": 1, "keywords": []}
    selected = _select_items_for_category(items, cfg, [], now)
    sources = [item["source"] for item in selected]
    assert sources.count("a") == 1
    assert len(selected) == 3


def test_anti_repeat_with_backfill() -> None:
    now = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    fresh_item = {
        "title": "Fresh headline",
        "teaser": "",
        "link": "https://example.com/fresh",
        "published": now - timedelta(hours=1),
        "source": "a",
    }
    stale_item = {
        "title": "Stale headline",
        "teaser": "",
        "link": "https://example.com/stale",
        "published": now - timedelta(hours=60),
        "source": "b",
    }
    history = [
        {
            "hash": title_hash("Fresh headline"),
            "date": "2025-01-10",
        }
    ]
    cfg = {"limit": 1, "fresh_hours": 36, "max_per_source": 2, "keywords": []}
    selected = _select_items_for_category([fresh_item, stale_item], cfg, history, now)
    assert [item["link"] for item in selected] == ["https://example.com/stale"]
