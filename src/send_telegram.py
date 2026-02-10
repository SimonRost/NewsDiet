"""Telegram delivery."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

_MAX_MESSAGE_LEN = 3800


def _display_name(key: str) -> str:
    return key.replace("_", " ").title()


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _main_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return ""
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _category_block(category: str, items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append(f"<u><b>{_escape_html(_display_name(category))}</b></u>")
    if not items:
        lines.append("- No items")
        return "\n".join(lines)
    for item in items:
        title = _escape_html(item.get("title", "").strip())
        teaser = _escape_html(item.get("teaser", "").strip())
        link = item.get("link", "").strip()
        lines.append(f"<b>{title}</b>")
        if teaser:
            lines.append(teaser)
        if link:
            safe_link = _escape_html(link)
            domain = _main_domain(link)
            label = "Full Article"
            if domain:
                label = f"Full Article ({domain})"
            lines.append(f"<a href=\"{safe_link}\">{_escape_html(label)}</a>")
        lines.append("")
    return "\n".join(lines).strip()


def build_message_chunks(
    items_by_category: dict[str, list[dict[str, Any]]],
    as_of: date,
) -> list[str]:
    header = f"Daily News Diet — {as_of.strftime('%Y-%m-%d')}"
    header = _escape_html(header)
    chunks: list[str] = []
    current = header

    for category, items in items_by_category.items():
        block = _category_block(category, items)
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= _MAX_MESSAGE_LEN:
            current = candidate
            continue
        if current:
            chunks.append(current.strip())
        block_with_header = f"{header}\n\n{block}"
        if len(block_with_header) <= _MAX_MESSAGE_LEN:
            current = block_with_header
        else:
            chunks.append(block)
            current = header

    if current:
        chunks.append(current.strip())

    return chunks


def _send_text(token: str, chat_id: str, text: str) -> bool:
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    ).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    request = urllib.request.Request(url, data=payload, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Telegram send failed: HTTP {exc.code} {exc.reason}")
        print(f"Response body: {body}")
        return False
    except urllib.error.URLError as exc:
        print(f"Telegram send failed: {exc}")
        return False

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("Telegram send failed: invalid JSON response")
        print(f"Response body: {raw}")
        return False

    if not isinstance(data, dict) or not data.get("ok"):
        print("Telegram send failed: unexpected response")
        print(f"Response body: {raw}")
        return False

    return True


def send_daily_digest(
    items_by_category: dict[str, list[dict[str, Any]]],
    as_of: date,
) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram env vars missing; skipping send.")
        return False

    chunks = build_message_chunks(items_by_category, as_of)
    for chunk in chunks:
        if not _send_text(token, chat_id, chunk):
            return False

    return True
