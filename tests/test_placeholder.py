from datetime import date, datetime, timezone
from pathlib import Path

from src.dedupe import dedupe_items, normalize_title
from src.keyword_filter import filter_by_keywords
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
