from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

NOW = datetime(2026, 11, 6, 12, 30, tzinfo=UTC)


def chart(**changes):
    meta = {
        "symbol": "NQ=F",
        "instrumentType": "FUTURE",
        "currency": "USD",
        "shortName": "Nasdaq 100 Dec26",
        "regularMarketPrice": 25125.5,
        "regularMarketTime": int(NOW.timestamp()) - 600,
        "previousClose": 25000,
        "chartPreviousClose": 24900,
        "regularMarketDayHigh": 25200,
        "regularMarketDayLow": 24800,
        "regularMarketVolume": 123456,
    }
    meta.update(changes)
    # Valid quote metadata can exist even when minute bars are empty.
    return {"chart": {"error": None, "result": [{"meta": meta}]}}


def test_intraday_quote_uses_provider_timestamp_and_reference_close():
    from technews.quotes import parse_quote

    quote = parse_quote(chart(), "NQ=F", now=NOW)
    assert quote.price == 25125.5
    assert quote.quoted_at == datetime(2026, 11, 6, 12, 20, tzinfo=UTC)
    assert quote.previous_close == 25000
    assert quote.change == 125.5
    assert quote.change_percent == pytest.approx(0.502)
    assert (quote.low, quote.high, quote.volume) == (24800, 25200, 123456)


@pytest.mark.parametrize(
    "changes",
    [
        {"symbol": "^NDX"},
        {"instrumentType": "INDEX"},
        {"regularMarketPrice": float("nan")},
        {"regularMarketPrice": True},
        {"regularMarketTime": None},
        {"regularMarketTime": False},
        {"regularMarketTime": float("inf")},
        {"regularMarketTime": NOW.timestamp() + 3600},
        {"regularMarketTime": -1},
    ],
)
def test_invalid_core_metadata_is_never_reported_as_a_current_future(changes):
    from technews.quotes import QuoteError, parse_quote

    with pytest.raises(QuoteError):
        parse_quote(chart(**changes), "NQ=F", now=NOW)


@pytest.mark.parametrize("payload", [{}, [], {"chart": {"result": []}}])
def test_empty_or_malformed_chart_fails_safely(payload):
    from technews.quotes import QuoteError, parse_quote

    with pytest.raises(QuoteError):
        parse_quote(payload, "NQ=F", now=NOW)


def test_optional_missing_fields_are_not_zero_and_close_fallback_is_explicit():
    from technews.quotes import parse_quote

    quote = parse_quote(
        chart(
            previousClose=None,
            chartPreviousClose=None,
            regularMarketDayHigh=float("nan"),
            regularMarketVolume=-1,
        ),
        "NQ=F",
        now=NOW,
    )
    assert quote.previous_close is None
    assert quote.change is None
    assert quote.change_percent is None
    assert quote.high is None
    assert quote.volume is None
    assert (
        parse_quote(chart(previousClose=None), "NQ=F", now=NOW).previous_close == 24900
    )


def test_negative_energy_price_preserves_absolute_change_without_bad_percentage():
    from technews.quotes import parse_quote

    quote = parse_quote(
        chart(symbol="CL=F", regularMarketPrice=-5, previousClose=-10),
        "CL=F",
        now=NOW,
    )
    assert quote.change == 5
    assert quote.change_percent is None


def test_quote_rendering_has_beijing_time_change_range_and_stale_weekend_warning():
    from technews.quotes import QuoteResult, parse_quote, render_quote_report

    results = (
        QuoteResult("纳指100期货", "NQ=F", parse_quote(chart(), "NQ=F", now=NOW)),
        QuoteResult("标普500期货", "ES=F", error="行情暂不可用"),
    )
    fresh = render_quote_report(results, NOW)
    assert "25,125.50" in fresh
    assert "+125.50" in fresh and "+0.50%" in fresh
    assert "2026-11-06 20:20:00" in fresh
    assert "24,800.00" in fresh and "25,200.00" in fresh
    assert "123,456" in fresh
    assert "参考前收" in fresh and "延迟行情" in fresh
    assert "Nasdaq 100 Dec26" in fresh
    assert "标普500期货" in fresh and "行情暂不可用" in fresh
    assert "报价较旧" not in fresh
    weekend = render_quote_report(results, NOW + timedelta(days=1))
    assert "报价较旧" in weekend and "可能休市或数据延迟" in weekend
    assert "2026-11-06 20:20:00" in weekend


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return deepcopy(self.payload)


class Session:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = 0

    def get(self, url, *, params, timeout):
        assert url.startswith("https://query")
        assert url.endswith("/v8/finance/chart/NQ%3DF")
        assert params == {"range": "1d", "interval": "1m"}
        assert timeout == 15
        self.calls += 1
        value = next(self.replies)
        if isinstance(value, Exception):
            raise value
        return Response(value)


def test_bounded_fetch_recovers_from_bad_first_response():
    from technews.quotes import fetch_quote

    session = Session([{}, chart()])
    assert fetch_quote("NQ=F", session=session, now=NOW).price == 25125.5


def test_fetch_failure_is_bounded_and_does_not_expose_response_details():
    from curl_cffi.requests.exceptions import RequestException

    from technews.quotes import QuoteError, fetch_quote

    session = Session([RequestException("private response"), {}])
    with pytest.raises(QuoteError) as error:
        fetch_quote("NQ=F", session=session, now=NOW)
    assert session.calls == 2
    assert "private response" not in str(error.value)


def test_collection_preserves_failed_and_successful_symbols():
    from technews.quotes import QuoteError, collect_quotes, parse_quote

    def fetch(symbol):
        if symbol == "ES=F":
            raise QuoteError("unavailable")
        return parse_quote(chart(), symbol, now=NOW)

    results = collect_quotes((("纳指", "NQ=F"), ("标普", "ES=F")), fetcher=fetch)
    assert results[0].quote.price == 25125.5
    assert results[1].quote is None and results[1].error


def test_older_config_without_futures_section_uses_compatible_defaults(tmp_path):
    from technews.settings import load_settings

    text = Path("config.toml").read_text("utf-8").split("\n[futures]")[0]
    path = tmp_path / "config.toml"
    path.write_text(text, "utf-8")
    assert load_settings(path).futures.tickers[0][1] == "NQ=F"


@pytest.mark.parametrize("replacement", ["0", "true"])
def test_invalid_staleness_setting_is_rejected(tmp_path, replacement):
    from technews.settings import ConfigError, load_settings

    text = Path("config.toml").read_text("utf-8")
    text = text.replace("max_age_minutes = 120", "max_age_minutes = " + replacement)
    path = tmp_path / "config.toml"
    path.write_text(text, "utf-8")
    with pytest.raises(ConfigError):
        load_settings(path)
