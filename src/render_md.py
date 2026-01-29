"""Markdown rendering."""

from __future__ import annotations

from datetime import date
from typing import Any


def _display_name(key: str) -> str:
    return key.replace("_", " ").title()


def render_markdown(
    items_by_category: dict[str, list[dict[str, Any]]],
    as_of: date,
) -> str:
    lines: list[str] = []
    lines.append(f"# Daily News Diet — {as_of.strftime('%A')}, {as_of.strftime('%Y-%m-%d')}")
    lines.append("")
    for category, items in items_by_category.items():
        lines.append(f"## {_display_name(category)}")
        if not items:
            lines.append("- No items")
            lines.append("")
            continue
        for item in items:
            title = item.get("title", "").strip()
            teaser = item.get("teaser", "").strip()
            link = item.get("link", "").strip()
            lines.append(f"- **{title}**")
            if teaser:
                lines.append(f"  - {teaser}")
            if link:
                lines.append(f"  - Link: {link}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
