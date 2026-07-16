from unittest.mock import Mock

import pytest
import requests

VALID_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
  <item>
    <title><![CDATA[<b>A &amp; B</b>]]></title>
    <link>https://example.com/a</link>
  </item>
  <item>
    <title>Unsafe link</title>
    <link>javascript:alert(1)</link>
  </item>
</channel></rss>
"""


def test_parse_rss_sanitizes_titles_and_rejects_unsafe_links():
    from technews.rss import NewsItem, parse_rss

    assert parse_rss(VALID_RSS, limit=3) == (
        NewsItem("A & B", "https://example.com/a"),
        NewsItem("Unsafe link", ""),
    )


def test_parse_rss_respects_item_limit():
    from technews.rss import parse_rss

    assert len(parse_rss(VALID_RSS, limit=1)) == 1


def test_parse_rss_rejects_malformed_xml():
    from technews.rss import parse_rss

    with pytest.raises(ValueError, match="Invalid RSS"):
        parse_rss(b"<rss>", limit=3)


def test_fetch_news_source_returns_safe_failure():
    from technews.rss import fetch_news_source

    session = Mock()
    session.get.side_effect = requests.RequestException("secret upstream detail")

    result = fetch_news_source(session, "测试源", "https://example.com/rss")

    assert result.name == "测试源"
    assert result.items == ()
    assert result.error == "获取失败"


def test_render_news_report_includes_success_and_failure_sections():
    from technews.rss import NewsItem, NewsSourceResult, render_news_report

    report = render_news_report(
        (
            NewsSourceResult("成功源", (NewsItem("A [title]", "https://example.com"),)),
            NewsSourceResult("失败源", error="获取失败"),
        )
    )

    assert "## 📰 成功源" in report
    assert "[A \\[title\\]](https://example.com)" in report
    assert "## ⚠️ 失败源" in report
    assert "获取失败" in report


def test_render_news_report_deduplicates_across_sources():
    from technews.rss import NewsItem, NewsSourceResult, render_news_report

    report = render_news_report(
        (
            NewsSourceResult(
                "首发源", (NewsItem("DeepSeek V4 发布！", "https://a.test/1"),)
            ),
            NewsSourceResult(
                "转载源", (NewsItem("deepseek v4 发布", "https://b.test/2"),)
            ),
            NewsSourceResult("失败源", error="获取失败"),
        ),
        keywords=("DeepSeek",),
        deduplicate=True,
    )

    assert report.casefold().count("deepseek v4") == 1
    assert "## 📰 转载源" not in report
    assert "## ⚠️ 失败源" in report


def test_render_news_report_highlights_keywords_case_insensitively():
    from technews.rss import NewsItem, NewsSourceResult, render_news_report

    report = render_news_report(
        (NewsSourceResult("来源", (NewsItem("DEEPSEEK 新模型", ""),)),),
        keywords=("DeepSeek",),
        deduplicate=False,
    )

    assert "1. 🔥 DEEPSEEK 新模型" in report
