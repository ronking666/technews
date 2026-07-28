import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

import yfinance as yf

from technews.config import (
    MARKET_HISTORY_PERIOD,
    MARKET_TICKERS,
    RANGE_DAYS,
    TREND_WINDOWS,
)
from technews.fred import fetch_fred_closes
from technews.market_calendar import expected_nasdaq_sessions

OFFICIAL_HISTORY_SERIES = {"^NDX": "NASDAQ100"}


@dataclass(frozen=True)
class MarketResult:
    name: str
    symbol: str
    current: float | None = None
    change: float | None = None
    pct_change: float | None = None
    data_date: date | None = None
    error: str | None = None
    trend_returns: tuple[tuple[int, float], ...] = ()
    range_window: int = 0
    range_low: float | None = None
    range_high: float | None = None


def market_result_from_history(
    name: str,
    symbol: str,
    history: Any,
    trend_windows: tuple[int, ...] = TREND_WINDOWS,
    range_days: int = RANGE_DAYS,
    fallback_closes: Mapping[date, float] | None = None,
) -> MarketResult:
    """Calculate the latest day-over-day change from a history frame."""
    if history is None or "Close" not in history:
        raise ValueError("Insufficient market history")

    observations: dict[date, float] = {}
    for index, raw_value in history["Close"].items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observed = index.date() if hasattr(index, "date") else index
        if isinstance(observed, date) and math.isfinite(value):
            observations[observed] = value

    for observed, raw_value in (fallback_closes or {}).items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if isinstance(observed, date) and math.isfinite(value):
            observations.setdefault(observed, value)

    closes = sorted(observations.items())
    if len(closes) < 2:
        raise ValueError("Insufficient market history")

    previous = closes[-2][1]
    current = closes[-1][1]
    if not math.isfinite(previous) or not math.isfinite(current) or previous == 0:
        raise ValueError("Invalid market history")

    change = current - previous
    pct_change = change / previous * 100
    data_date = closes[-1][0]
    if not isinstance(data_date, date):
        raise ValueError("Invalid market date")

    trend_returns = []
    for window in trend_windows:
        if window < 1 or len(closes) <= window:
            continue
        baseline = closes[-(window + 1)][1]
        if math.isfinite(baseline) and baseline != 0:
            trend_returns.append((window, (current / baseline - 1) * 100))

    range_values = [
        value for _, value in closes[-max(1, range_days) :] if math.isfinite(value)
    ]

    return MarketResult(
        name=name,
        symbol=symbol,
        current=current,
        change=change,
        pct_change=pct_change,
        data_date=data_date,
        trend_returns=tuple(trend_returns),
        range_window=len(range_values),
        range_low=min(range_values) if range_values else None,
        range_high=max(range_values) if range_values else None,
    )


def fetch_market_result(
    name: str,
    symbol: str,
    ticker_factory: Callable[[str], Any] = yf.Ticker,
    attempts: int = 3,
    pause: Callable[[float], None] = time.sleep,
    official_history_loader: Callable[
        [str, date, date], Mapping[date, float]
    ] = fetch_fred_closes,
) -> MarketResult:
    """Fetch one market symbol with bounded attempts and safe errors."""
    attempts = max(1, attempts)
    for attempt in range(attempts):
        try:
            ticker = ticker_factory(symbol)
            history = ticker.history(
                period=MARKET_HISTORY_PERIOD,
                timeout=15,
                raise_errors=True,
            )
            fallback_closes: Mapping[date, float] | None = None
            series_id = OFFICIAL_HISTORY_SERIES.get(symbol)
            if series_id is not None:
                yahoo_closes = history["Close"].dropna()
                if len(yahoo_closes) < 2:
                    raise ValueError("Insufficient Yahoo market history")
                first_index = yahoo_closes.index[0]
                last_index = yahoo_closes.index[-1]
                start = (
                    first_index.date() if hasattr(first_index, "date") else first_index
                )
                end = last_index.date() if hasattr(last_index, "date") else last_index
                if not isinstance(start, date) or not isinstance(end, date):
                    raise ValueError("Invalid Yahoo market date")
                fallback_closes = official_history_loader(series_id, start, end)
                expected_sessions = expected_nasdaq_sessions(start, end)
                if not expected_sessions.issubset(fallback_closes):
                    raise ValueError("Incomplete official market history")

            return market_result_from_history(
                name,
                symbol,
                history,
                fallback_closes=fallback_closes,
            )
        except Exception:
            if attempt + 1 < attempts:
                pause(float(attempt + 1))

    return MarketResult(name=name, symbol=symbol, error="获取失败")


def collect_configured_markets() -> tuple[MarketResult, ...]:
    return tuple(fetch_market_result(name, symbol) for name, symbol in MARKET_TICKERS)


def _signed_percentage(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def render_market_report(results: tuple[MarketResult, ...]) -> str:
    sections = []
    for result in results:
        if result.error is not None or result.current is None:
            sections.append(f"### ⚠️ {result.name}\n> {result.error or '暂无有效数据'}")
            continue

        change = result.change or 0.0
        pct_change = result.pct_change or 0.0
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        sign = "+" if change > 0 else ""
        lines = [
            f"### {emoji} {result.name}",
            "",
            f"- **数据日期**：{result.data_date:%Y-%m-%d}",
            f"- **最新价**：**{result.current:.2f}**",
            f"- **当日涨跌**：{sign}{change:.2f}（{sign}{pct_change:.2f}%）",
        ]
        for window, value in result.trend_returns:
            lines.append(f"- **{window}日趋势**：{_signed_percentage(value)}")
        if (
            result.range_window
            and result.range_low is not None
            and result.range_high is not None
        ):
            lines.append(
                f"- **{result.range_window}日区间**："
                f"{result.range_low:.2f} ～ {result.range_high:.2f}"
            )
        sections.append("\n".join(lines))

    if not sections:
        return "### ⚠️ 财经行情\n> 未配置行情标的"
    return "\n\n---\n\n".join(sections)
