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


def test_market_result_calculates_trends_and_range():
    from technews.market import market_result_from_history

    values = tuple(float(value) for value in range(100, 125))
    frame = pd.DataFrame(
        {"Close": values},
        index=pd.date_range("2026-06-01", periods=len(values), freq="D"),
    )

    result = market_result_from_history(
        "指数", "IDX", frame, trend_windows=(5, 20), range_days=20
    )

    assert result.trend_returns == (
        (5, pytest.approx((124 / 119 - 1) * 100)),
        (20, pytest.approx((124 / 104 - 1) * 100)),
    )
    assert result.range_window == 20
    assert result.range_low == 105.0
    assert result.range_high == 124.0


def test_market_result_fills_missing_ndx_close_before_calculating_change():
    from technews.market import market_result_from_history

    frame = pd.DataFrame(
        {
            "Close": [
                28592.66,
                28604.23,
                29155.18,
                28998.10,
                28454.81,
                28039.21,
            ]
        },
        index=pd.to_datetime(
            [
                "2026-07-17",
                "2026-07-20",
                "2026-07-21",
                "2026-07-22",
                "2026-07-23",
                "2026-07-27",
            ]
        ),
    )

    result = market_result_from_history(
        "纳斯达克100指数",
        "^NDX",
        frame,
        trend_windows=(5,),
        range_days=5,
        fallback_closes={date(2026, 7, 24): 28128.34},
    )

    assert result.change == pytest.approx(-89.13)
    assert result.pct_change == pytest.approx(-0.316866, rel=1e-5)
    window, value = result.trend_returns[0]
    assert window == 5
    assert value == pytest.approx((28039.21 / 28604.23 - 1) * 100)


def test_market_result_preserves_yahoo_values_and_calculates_20_day_trend():
    from technews.market import market_result_from_history

    dates = pd.bdate_range(end="2026-07-27", periods=22)
    values = tuple(float(value) for value in range(100, 122))
    frame = pd.DataFrame({"Close": values}, index=dates)

    result = market_result_from_history(
        "纳斯达克100指数",
        "^NDX",
        frame,
        trend_windows=(5, 20),
        fallback_closes={
            dates[-2].date(): 999.0,
            dates[-21].date(): 999.0,
        },
    )

    assert result.current == 121.0
    assert result.change == 1.0
    assert result.trend_returns == (
        (5, pytest.approx((121 / 116 - 1) * 100)),
        (20, pytest.approx((121 / 101 - 1) * 100)),
    )


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


def test_fetch_ndx_uses_official_history_to_fill_missing_close():
    from technews.market import fetch_market_result

    frame = pd.DataFrame(
        {"Close": [28454.81, 28039.21]},
        index=pd.to_datetime(["2026-07-23", "2026-07-27"]),
    )

    class Ticker:
        def history(self, **kwargs):
            return frame

    def official_history_loader(series_id, start, end):
        assert series_id == "NASDAQ100"
        assert start == date(2026, 7, 23)
        assert end == date(2026, 7, 27)
        return {
            date(2026, 7, 23): 28454.81,
            date(2026, 7, 24): 28128.34,
        }

    result = fetch_market_result(
        "纳斯达克100指数",
        "^NDX",
        ticker_factory=lambda symbol: Ticker(),
        attempts=1,
        official_history_loader=official_history_loader,
    )

    assert result.error is None
    assert result.change == pytest.approx(-89.13)


def test_fetch_ndx_fails_closed_when_official_history_is_unavailable():
    from technews.fred import MarketDataError
    from technews.market import fetch_market_result

    class Ticker:
        def history(self, **kwargs):
            return history()

    def failing_loader(*args):
        raise MarketDataError("safe failure")

    result = fetch_market_result(
        "纳斯达克100指数",
        "^NDX",
        ticker_factory=lambda symbol: Ticker(),
        attempts=1,
        official_history_loader=failing_loader,
    )

    assert result.error == "获取失败"


def test_fetch_ndx_fails_closed_when_official_history_is_incomplete():
    from technews.market import fetch_market_result

    frame = pd.DataFrame(
        {"Close": [28454.81, 28039.21]},
        index=pd.to_datetime(["2026-07-23", "2026-07-27"]),
    )

    class Ticker:
        def history(self, **kwargs):
            return frame

    result = fetch_market_result(
        "纳斯达克100指数",
        "^NDX",
        ticker_factory=lambda symbol: Ticker(),
        attempts=1,
        official_history_loader=lambda *args: {date(2026, 7, 23): 28454.81},
    )

    assert result.error == "获取失败"


def test_fetch_ndx_allows_a_standard_market_holiday_gap():
    from technews.market import fetch_market_result

    frame = pd.DataFrame(
        {"Close": [29000.0, 29100.0]},
        index=pd.to_datetime(["2026-07-02", "2026-07-06"]),
    )

    class Ticker:
        def history(self, **kwargs):
            return frame

    result = fetch_market_result(
        "纳斯达克100指数",
        "^NDX",
        ticker_factory=lambda symbol: Ticker(),
        attempts=1,
        official_history_loader=lambda *args: {date(2026, 7, 2): 29000.0},
    )

    assert result.error is None
    assert result.change == 100.0


def test_fetch_non_ndx_market_does_not_require_official_history():
    from technews.market import fetch_market_result

    class Ticker:
        def history(self, **kwargs):
            return history()

    def forbidden_loader(*args):
        raise AssertionError("official loader should not be called")

    result = fetch_market_result(
        "黄金",
        "GC=F",
        ticker_factory=lambda symbol: Ticker(),
        attempts=1,
        official_history_loader=forbidden_loader,
    )

    assert result.error is None
    assert result.current == 103.0


def test_render_market_report_includes_date_and_failure():
    from technews.market import MarketResult, render_market_report

    report = render_market_report(
        (
            MarketResult("指数", "IDX", 103.0, 3.0, 3.0, date(2026, 7, 15)),
            MarketResult("黄金", "GC=F", error="获取失败"),
        )
    )

    assert "- **数据日期**：2026-07-15" in report
    assert "- **最新价**：**103.00**" in report
    assert "- **当日涨跌**：+3.00（+3.00%）" in report
    assert "黄金" in report and "获取失败" in report


def test_render_market_report_includes_trends_and_range():
    from technews.market import MarketResult, render_market_report

    result = MarketResult(
        "指数",
        "IDX",
        124.0,
        1.0,
        0.81,
        date(2026, 7, 15),
        trend_returns=((5, 4.2), (20, 19.23)),
        range_window=20,
        range_low=105.0,
        range_high=124.0,
    )

    report = render_market_report((result,))

    assert "- **数据日期**：2026-07-15" in report
    assert "- **最新价**：**124.00**" in report
    assert "- **当日涨跌**：+1.00（+0.81%）" in report
    assert "- **5日趋势**：+4.20%" in report
    assert "- **20日趋势**：+19.23%" in report
    assert "- **20日区间**：105.00 ～ 124.00" in report
    assert " ｜ " not in report
