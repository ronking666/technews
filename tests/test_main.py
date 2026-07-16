from datetime import UTC, datetime
from unittest.mock import Mock


def news_results():
    from technews.rss import NewsItem, NewsSourceResult

    return (
        NewsSourceResult("IT之家", (NewsItem("新闻", "https://example.com"),)),
        NewsSourceResult("备用源", error="获取失败"),
    )


def test_missing_sendkey_fails_without_notification():
    from main import run

    notifier = Mock()

    assert run("", results=news_results(), notifier=notifier) == 2
    notifier.assert_not_called()


def test_partial_news_failure_still_sends_available_content():
    from main import run

    notifier = Mock()
    now = datetime(2026, 7, 15, 21, 30, tzinfo=UTC)

    assert run("key", now=now, results=news_results(), notifier=notifier) == 0

    _, title, content = notifier.call_args.args
    assert "2026年07月16日" in title
    assert "IT之家" in content
    assert "备用源" in content


def test_total_news_failure_sends_summary_then_fails():
    from main import run
    from technews.rss import NewsSourceResult

    notifier = Mock()
    results = (NewsSourceResult("IT之家", error="获取失败"),)

    assert run("key", results=results, notifier=notifier) == 1
    notifier.assert_called_once()


def test_notification_failure_returns_failure_without_leaking_key(capsys):
    from main import run
    from technews.notifier import NotificationError

    def notifier(*args):
        raise NotificationError("ServerChan request failed")

    assert run("very-secret", results=news_results(), notifier=notifier) == 1
    assert "very-secret" not in capsys.readouterr().out


def test_news_report_prepends_ai_summary():
    from main import run

    notifier = Mock()
    summarizer = Mock(return_value="今日重点")

    assert (
        run(
            "key",
            results=news_results(),
            notifier=notifier,
            summarizer=summarizer,
        )
        == 0
    )

    content = notifier.call_args.args[2]
    assert content.startswith("## 🤖 DeepSeek AI 摘要")
    assert "今日重点" in content


def test_news_summary_failure_still_sends_original_report():
    from main import run
    from technews.ai import SummaryError

    notifier = Mock()

    def summarizer(*args):
        raise SummaryError("DeepSeek summary request failed")

    assert (
        run(
            "key",
            results=news_results(),
            notifier=notifier,
            summarizer=summarizer,
        )
        == 0
    )
    assert "DeepSeek AI 摘要" not in notifier.call_args.args[2]
