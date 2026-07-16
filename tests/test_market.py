from datetime import date

import pandas as pd
import pytest


def history(values=(100.0, 103.0)):
    return pd.DataFrame(
        {"Close": values},
        index=pd.to_datetime(["2026-07-14", "2026-07-15"]),
    )


@pytest.mark.parametrize(
    ("values", "change", "pct_change"),
    [
        ((100.0, 103.0), 3.0, 3.0),
        ((100.0, 97.0), -3.0, -3.0),
        ((100.0, 100.0), 0.0, 0.0),
    ],
)
def test_market_result_calculates_change_and_date(values, change, pct_change):
    from technews.market import market_result_from_history

    result = market_result_from_history("指数", "IDX", history(values))

    assert result.current == values[-1]
    assert result.change == change
    assert result.pct_change == pytest.approx(pct_change)
    assert result.data_date == date(2026, 7, 15)


def test_market_result_rejects_insufficient_history():
    from technews.market import market_result_from_history

    frame = pd.DataFrame(
        {"Close": [100.0]},
        index=pd.to_datetime(["2026-07-15"]),
    )

    with pytest.raises(ValueError, match="Insufficient"):
        market_result_from_history("指数", "IDX", frame)


def test_fetch_market_result_retries_then_succeeds():
    from technews.market import fetch_market_result

    class Ticker:
        calls = 0

        def history(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary secret detail")
            return history()

    ticker = Ticker()
    pauses = []

    result = fetch_market_result(
        "指数",
        "IDX",
        ticker_factory=lambda symbol: ticker,
        attempts=3,
        pause=pauses.append,
    )

    assert result.error is None
    assert ticker.calls == 2
    assert pauses == [1.0]


def test_fetch_market_result_returns_safe_failure_after_attempts():
    from technews.market import fetch_market_result

    class Ticker:
        def history(self, **kwargs):
            raise RuntimeError("temporary secret detail")

    result = fetch_market_result(
        "指数",
        "IDX",
        ticker_factory=lambda symbol: Ticker(),
        attempts=2,
        pause=lambda seconds: None,
    )

    assert result.error == "获取失败"
    assert "secret" not in result.error


def test_fetch_market_result_handles_ticker_construction_failure():
    from technews.market import fetch_market_result

    def fail_to_create(symbol):
        raise RuntimeError("constructor secret detail")

    result = fetch_market_result(
        "指数",
        "IDX",
        ticker_factory=fail_to_create,
        attempts=1,
        pause=lambda seconds: None,
    )

    assert result.error == "获取失败"


def test_render_market_report_includes_date_and_failure():
    from technews.market import MarketResult, render_market_report

    report = render_market_report(
        (
            MarketResult("指数", "IDX", 103.0, 3.0, 3.0, date(2026, 7, 15)),
            MarketResult("黄金", "GC=F", error="获取失败"),
        )
    )

    assert "数据日期：2026-07-15" in report
    assert "103.00" in report
    assert "+3.00 (+3.00%)" in report
    assert "黄金" in report and "获取失败" in report
