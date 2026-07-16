from dataclasses import dataclass
from html import unescape
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests

from technews.config import REQUEST_TIMEOUT, RSS_SOURCES


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


def parse_rss(content: bytes, limit: int = 8) -> tuple[NewsItem, ...]:
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
    limit: int = 8,
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
    limit: int = 8,
) -> tuple[NewsSourceResult, ...]:
    return tuple(
        fetch_news_source(session, name, url, limit=limit)
        for name, url in RSS_SOURCES
    )


def _escape_markdown_label(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def render_news_report(results: tuple[NewsSourceResult, ...]) -> str:
    sections = []
    for result in results:
        if result.items:
            lines = [f"## 📰 {result.name}"]
            for index, item in enumerate(result.items, 1):
                title = _escape_markdown_label(item.title)
                if item.link:
                    lines.append(f"{index}. [{title}]({item.link})")
                else:
                    lines.append(f"{index}. {title}")
            sections.append("\n".join(lines))
        else:
            sections.append(f"## ⚠️ {result.name}\n> {result.error or '未返回新闻'}")

    if not sections:
        return "## ⚠️ 科技资讯\n> 未配置可用新闻源"
    return "\n\n".join(sections)
