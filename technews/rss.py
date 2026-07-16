import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

import requests

from technews.config import (
    NEWS_DEDUPLICATE,
    NEWS_ITEM_LIMIT,
    NEWS_KEYWORDS,
    REQUEST_TIMEOUT,
    RSS_SOURCES,
)

RSS_HEADERS = {
    "User-Agent": "technews-daily-report/1.0 (+https://github.com/ronking666/technews)",
    "Accept": "application/rss+xml, application/xml, text/xml",
}
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str = ""


@dataclass(frozen=True)
class NewsSourceResult:
    name: str
    items: tuple[NewsItem, ...] = ()
    error: str | None = None


def _clean_title(value: str | None) -> str:
    text = unescape(value or "")
    text = _TAG_RE.sub("", text)
    text = " ".join(text.split())
    return text or "无标题"


def _safe_link(value: str | None) -> str:
    link = (value or "").strip()
    parsed = urlparse(link)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return link
    return ""


def parse_rss(content: bytes, limit: int = NEWS_ITEM_LIMIT) -> tuple[NewsItem, ...]:
    """Parse a conventional RSS feed into sanitized news items."""
    if limit < 1:
        return ()
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        raise ValueError("Invalid RSS document") from None

    items = []
    for element in root.findall(".//item")[:limit]:
        items.append(
            NewsItem(
                title=_clean_title(element.findtext("title")),
                link=_safe_link(element.findtext("link")),
            )
        )
    return tuple(items)


def fetch_news_source(
    session: requests.Session,
    name: str,
    url: str,
    limit: int = NEWS_ITEM_LIMIT,
) -> NewsSourceResult:
    """Fetch one source without exposing upstream exception details."""
    try:
        response = session.get(
            url,
            headers=RSS_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        items = parse_rss(response.content, limit=limit)
    except (requests.RequestException, ValueError):
        return NewsSourceResult(name=name, error="获取失败")

    if not items:
        return NewsSourceResult(name=name, error="未返回新闻")
    return NewsSourceResult(name=name, items=items)


def collect_configured_news(
    session: requests.Session,
    limit: int = NEWS_ITEM_LIMIT,
) -> tuple[NewsSourceResult, ...]:
    return tuple(
        fetch_news_source(session, name, url, limit=limit) for name, url in RSS_SOURCES
    )


def _escape_markdown_label(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def normalize_news_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).casefold()
    return "".join(character for character in normalized if character.isalnum())


def deduplicate_news(
    results: tuple[NewsSourceResult, ...],
) -> tuple[NewsSourceResult, ...]:
    seen = set()
    filtered = []
    for result in results:
        if not result.items:
            filtered.append(result)
            continue
        items = []
        for item in result.items:
            key = normalize_news_title(item.title)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            items.append(item)
        if items:
            filtered.append(NewsSourceResult(result.name, tuple(items)))
    return tuple(filtered)


def _matches_keyword(title: str, keywords: tuple[str, ...]) -> bool:
    normalized_title = unicodedata.normalize("NFKC", title).casefold()
    return any(
        unicodedata.normalize("NFKC", keyword).casefold() in normalized_title
        for keyword in keywords
    )


def render_news_report(
    results: tuple[NewsSourceResult, ...],
    keywords: tuple[str, ...] = NEWS_KEYWORDS,
    deduplicate: bool = NEWS_DEDUPLICATE,
) -> str:
    if deduplicate:
        results = deduplicate_news(results)
    sections = []
    for result in results:
        if result.items:
            lines = [f"## 📰 {result.name}"]
            for index, item in enumerate(result.items, 1):
                title = _escape_markdown_label(item.title)
                prefix = "🔥 " if _matches_keyword(item.title, keywords) else ""
                if item.link:
                    lines.append(f"{index}. {prefix}[{title}]({item.link})")
                else:
                    lines.append(f"{index}. {prefix}{title}")
            sections.append("\n".join(lines))
        else:
            sections.append(f"## ⚠️ {result.name}\n> {result.error or '未返回新闻'}")

    if not sections:
        return "## ⚠️ 科技资讯\n> 未配置可用新闻源"
    return "\n\n".join(sections)
