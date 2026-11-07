from datetime import UTC, datetime

import pytest

NOW = datetime(2026, 11, 6, 12, 30, tzinfo=UTC)


def results():
    from technews.quotes import Quote, QuoteResult

    quote = Quote(25000, NOW, 24900, 25100, 24800, 1234, "Nasdaq 100 Dec26", "USD")
    return (QuoteResult("纳指100期货", "NQ=F", quote),)


def test_night_report_sends_timestamped_data_without_ai():
    import futures

    messages = []
    code = futures.run(
        "test-key",
        now=NOW,
        results=results(),
        notifier=lambda *args: messages.append(args),
    )
    assert code == 0
    key, title, body = messages[0]
    assert key == "test-key"
    assert "期货晚报" in title and "2026年11月06日" in title
    assert "2026-11-06 20:30:00" in body
    assert "25,000.00" in body


def test_missing_key_stops_before_collection(monkeypatch):
    import futures

    def forbidden():
        pytest.fail("should not collect quotes without a key")

    monkeypatch.setattr(futures, "collect_configured_quotes", forbidden)
    assert futures.run("") == 2


def test_failed_notification_exits_safely(capsys):
    import futures
    from technews.notifier import NotificationError

    def fail(*args):
        raise NotificationError("test-key private server response")

    assert futures.run("test-key", now=NOW, results=results(), notifier=fail) == 1
    assert "test-key" not in capsys.readouterr().out


def test_partial_failure_keeps_other_data_and_can_complete():
    import futures
    from technews.quotes import QuoteResult

    messages = []
    data = results() + (QuoteResult("黄金", "GC=F", error="failed"),)
    assert (
        futures.run(
            "key", now=NOW, results=data, notifier=lambda *args: messages.append(args)
        )
        == 0
    )
    assert "行情暂不可用" in messages[0][2]
    assert "25,000.00" in messages[0][2]


def test_all_failed_sends_failure_summary_and_remains_retryable():
    import futures
    from technews.quotes import QuoteResult

    messages = []
    assert (
        futures.run(
            "key",
            now=NOW,
            results=(QuoteResult("纳指", "NQ=F", error="failed"),),
            notifier=lambda *args: messages.append(args),
        )
        == 1
    )
    assert "主标的纳指100期货暂不可用" in messages[0][2]


def test_missing_nasdaq_remains_retryable_even_if_related_market_succeeds():
    import futures
    from technews.quotes import QuoteResult

    messages = []
    data = (
        QuoteResult("纳指", "NQ=F", error="failed"),
        QuoteResult("标普", "ES=F", results()[0].quote),
    )
    assert (
        futures.run(
            "key", now=NOW, results=data, notifier=lambda *args: messages.append(args)
        )
        == 1
    )
    assert "主标的纳指100期货暂不可用" in messages[0][2]


def test_preview_fetches_without_key_or_notification(monkeypatch, capsys):
    import futures

    monkeypatch.delenv("SERVERCHAN_SENDKEY", raising=False)
    monkeypatch.setattr(futures, "collect_configured_quotes", results)
    assert futures.main(["--preview"]) == 0
    assert "25,000.00" in capsys.readouterr().out


def test_preview_fails_if_main_nasdaq_quote_is_missing(monkeypatch):
    import futures

    monkeypatch.setattr(futures, "collect_configured_quotes", lambda: ())
    assert futures.main(["--preview"]) == 1
