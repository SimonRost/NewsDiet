"""Telegram delivery."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

_MAX_MESSAGE_LEN = 3800

_LOGGER = logging.getLogger(__name__)


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


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 1:
        return ""
    return text[: max_len - 1] + "…"


def _build_item_block(item: dict[str, Any], html: bool, max_len: int) -> str:
    title = item.get("title", "").strip()
    teaser = item.get("teaser", "").strip()
    link = item.get("link", "").strip()

    domain = _main_domain(link) if link else ""
    label = "Full Article"
    if domain:
        label = f"Full Article ({domain})"

    if html:
        title = _escape_html(title)
        teaser = _escape_html(teaser)
        link = _escape_html(link)
        label = _escape_html(label)

    title_line = f"<b>{title}</b>" if html else title
    link_line = (
        f"<a href=\"{link}\">{label}</a>" if (html and link) else ""
    )
    if not html and link:
        link_line = f"{label}: {link}"

    lines = [title_line]
    if teaser:
        lines.append(teaser)
    if link_line:
        lines.append(link_line)

    block = "\n".join(lines)
    if len(block) <= max_len:
        return block

    if teaser:
        teaser = _truncate(teaser, max_len)
        lines = [title_line, teaser]
        if link_line:
            lines.append(link_line)
        block = "\n".join(lines)
    if len(block) <= max_len:
        return block

    title_line = _truncate(title_line, max_len)
    lines = [title_line]
    if link_line:
        lines.append(link_line)
    return "\n".join(lines)


def build_message_chunks(
    items_by_category: dict[str, list[dict[str, Any]]],
    as_of: date,
    html: bool = True,
) -> list[str]:
    header = f"Daily News Diet — {as_of.strftime('%Y-%m-%d')}"
    if html:
        header = _escape_html(header)

    chunks: list[str] = []
    current = header

    for category, items in items_by_category.items():
        heading = _display_name(category)
        if html:
            heading = f"<u><b>{_escape_html(heading)}</b></u>"

        category_items: list[dict[str, Any] | None] = []
        if not items:
            category_items.append(None)
        else:
            category_items.extend(items)

        started_category = False
        for item in category_items:
            if item is None:
                item_block = "- No items"
            else:
                item_block = _build_item_block(item, html, _MAX_MESSAGE_LEN)
            block_lines = [heading, item_block] if not started_category else [item_block]
            block = "\n".join(block_lines)
            candidate = f"{current}\n\n{block}" if current else block
            if len(candidate) <= _MAX_MESSAGE_LEN:
                current = candidate
                started_category = True
                continue

            if current:
                chunks.append(current.strip())
                started_category = False

            available = _MAX_MESSAGE_LEN - len(f"{header}\n\n{heading}\n")
            if item is None:
                adjusted_item = "- No items"
            else:
                adjusted_item = _build_item_block(item, html, max(available, 1))
            block = "\n".join([heading, adjusted_item])
            current = f"{header}\n\n{block}"
            if len(current) > _MAX_MESSAGE_LEN:
                chunks.append(block.strip())
                current = header
                started_category = False
            else:
                started_category = True

    if current:
        chunks.append(current.strip())

    return chunks


def _send_text(token: str, chat_id: str, text: str, parse_mode: str | None) -> bool:
    payload_dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload_dict["parse_mode"] = parse_mode
    payload = urllib.parse.urlencode(payload_dict).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    request = urllib.request.Request(url, data=payload, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        _LOGGER.warning("Telegram send failed: HTTP %s %s", exc.code, exc.reason)
        _LOGGER.debug("Telegram response body: %s", body)
        return False
    except urllib.error.URLError as exc:
        _LOGGER.warning("Telegram send failed: %s", exc)
        return False

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _LOGGER.warning("Telegram send failed: invalid JSON response")
        _LOGGER.debug("Telegram response body: %s", raw)
        return False

    if not isinstance(data, dict) or not data.get("ok"):
        _LOGGER.warning("Telegram send failed: unexpected response")
        _LOGGER.debug("Telegram response body: %s", raw)
        return False

    return True


def send_daily_digest(
    items_by_category: dict[str, list[dict[str, Any]]],
    as_of: date,
) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        _LOGGER.warning("Telegram env vars missing; skipping send.")
        return False

    chunks = build_message_chunks(items_by_category, as_of, html=True)
    for chunk in chunks:
        if _send_text(token, chat_id, chunk, "HTML"):
            continue
        _LOGGER.warning("Telegram HTML send failed; retrying with plain text.")
        text_chunks = build_message_chunks(items_by_category, as_of, html=False)
        for text_chunk in text_chunks:
            if not _send_text(token, chat_id, text_chunk, None):
                return False
        return True

    return True
