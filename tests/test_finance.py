from datetime import UTC, date, datetime
from unittest.mock import Mock


def market_results():
    from technews.market import MarketResult

    return (
        MarketResult("指数", "IDX", 103.0, 3.0, 3.0, date(2026, 7, 15)),
        MarketResult("黄金", "GC=F", error="获取失败"),
    )


def test_missing_sendkey_fails_without_finance_notification():
    from finance import run

    notifier = Mock()

    assert run("", results=market_results(), notifier=notifier) == 2
    notifier.assert_not_called()


def test_partial_market_failure_still_sends_available_content():
    from finance import run

    notifier = Mock()
    now = datetime(2026, 7, 15, 22, 15, tzinfo=UTC)

    assert run("key", now=now, results=market_results(), notifier=notifier) == 0

    _, title, content = notifier.call_args.args
    assert "2026年07月16日" in title
    assert "指数" in content
    assert "黄金" in content


def test_total_market_failure_sends_summary_then_fails():
    from finance import run
    from technews.market import MarketResult

    notifier = Mock()
    results = (MarketResult("指数", "IDX", error="获取失败"),)

    assert run("key", results=results, notifier=notifier) == 1
    notifier.assert_called_once()


def test_finance_notification_failure_hides_key(capsys):
    from finance import run
    from technews.notifier import NotificationError

    def notifier(*args):
        raise NotificationError("ServerChan request failed")

    assert run("very-secret", results=market_results(), notifier=notifier) == 1
    assert "very-secret" not in capsys.readouterr().out


def test_finance_report_prepends_ai_summary():
    from finance import run

    notifier = Mock()
    summarizer = Mock(return_value="行情重点")

    assert (
        run(
            "key",
            results=market_results(),
            notifier=notifier,
            summarizer=summarizer,
        )
        == 0
    )

    content = notifier.call_args.args[2]
    assert content.startswith("## 🤖 DeepSeek AI 摘要")
    assert "行情重点" in content
