from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
import math
import time
from typing import Any

import yfinance as yf

from technews.config import MARKET_TICKERS


@dataclass(frozen=True)
class MarketResult:
    name: str
    symbol: str
    current: float | None = None
    change: float | None = None
    pct_change: float | None = None
    data_date: date | None = None
    error: str | None = None


def market_result_from_history(name: str, symbol: str, history: Any) -> MarketResult:
    """Calculate the latest day-over-day change from a history frame."""
    if history is None or "Close" not in history:
        raise ValueError("Insufficient market history")

    closes = history["Close"].dropna()
    if len(closes) < 2:
        raise ValueError("Insufficient market history")

    previous = float(closes.iloc[-2])
    current = float(closes.iloc[-1])
    if not math.isfinite(previous) or not math.isfinite(current) or previous == 0:
        raise ValueError("Invalid market history")

    change = current - previous
    pct_change = change / previous * 100
    latest_index = closes.index[-1]
    data_date = latest_index.date() if hasattr(latest_index, "date") else latest_index
    if not isinstance(data_date, date):
        raise ValueError("Invalid market date")

    return MarketResult(
        name=name,
        symbol=symbol,
        current=current,
        change=change,
        pct_change=pct_change,
        data_date=data_date,
    )


def fetch_market_result(
    name: str,
    symbol: str,
    ticker_factory: Callable[[str], Any] = yf.Ticker,
    attempts: int = 3,
    pause: Callable[[float], None] = time.sleep,
) -> MarketResult:
    """Fetch one market symbol with bounded attempts and safe errors."""
    attempts = max(1, attempts)
    ticker = ticker_factory(symbol)
    for attempt in range(attempts):
        try:
            history = ticker.history(
                period="7d",
                timeout=15,
                raise_errors=True,
            )
            return market_result_from_history(name, symbol, history)
        except Exception:
            if attempt + 1 < attempts:
                pause(float(attempt + 1))

    return MarketResult(name=name, symbol=symbol, error="获取失败")


def collect_configured_markets() -> tuple[MarketResult, ...]:
    return tuple(fetch_market_result(name, symbol) for name, symbol in MARKET_TICKERS)


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
        sections.append(
            f"### {emoji} {result.name}\n"
            f"> 数据日期：{result.data_date:%Y-%m-%d}\n> "
            f"最新价：**{result.current:.2f}** ｜ "
            f"涨跌：{sign}{change:.2f} ({sign}{pct_change:.2f}%)"
        )

    if not sections:
        return "### ⚠️ 财经行情\n> 未配置行情标的"
    return "\n\n---\n\n".join(sections)

