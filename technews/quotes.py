"""Bounded collection and rendering of Yahoo's delayed intraday quotes."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote as urlquote

from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException

from technews.config import APP_TIMEZONE, FUTURES_SETTINGS


class QuoteError(RuntimeError):
    """A quote is unavailable or cannot be safely interpreted."""


@dataclass(frozen=True)
class Quote:
    price: float
    quoted_at: datetime
    previous_close: float | None
    high: float | None
    low: float | None
    volume: float | None
    contract_name: str
    currency: str

    @property
    def change(self) -> float | None:
        if self.previous_close is None:
            return None
        return self.price - self.previous_close

    @property
    def change_percent(self) -> float | None:
        if self.previous_close is None or self.previous_close <= 0:
            return None
        return (self.price - self.previous_close) / self.previous_close * 100


@dataclass(frozen=True)
class QuoteResult:
    name: str
    symbol: str
    quote: Quote | None = None
    error: str | None = None


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) else None


def _label(value) -> str:
    return " ".join(value.split())[:100] if isinstance(value, str) else ""


def parse_quote(payload, symbol: str, *, now: datetime | None = None) -> Quote:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise QuoteError("报价校验需要带时区的时间")
    try:
        chart = payload["chart"]
        if chart.get("error"):
            raise QuoteError("行情接口未返回有效报价")
        meta = chart["result"][0]["meta"]
        if meta.get("symbol") != symbol:
            raise QuoteError("行情代码不匹配")
        if symbol.endswith("=F") and meta.get("instrumentType") != "FUTURE":
            raise QuoteError("未取得期货报价")
        price = _number(meta.get("regularMarketPrice"))
        timestamp = _number(meta.get("regularMarketTime"))
        if price is None or timestamp is None or timestamp <= 0:
            raise QuoteError("缺少有效价格或报价时间")
        quoted_at = datetime.fromtimestamp(timestamp, UTC)
        if quoted_at > current + timedelta(minutes=5):
            raise QuoteError("报价时间异常")
        previous_close = _number(meta.get("previousClose"))
        if previous_close is None:
            previous_close = _number(meta.get("chartPreviousClose"))
        high = _number(meta.get("regularMarketDayHigh"))
        low = _number(meta.get("regularMarketDayLow"))
        if high is not None and low is not None and high < low:
            high = low = None
        volume = _number(meta.get("regularMarketVolume"))
        if volume is not None and volume < 0:
            volume = None
        return Quote(
            price,
            quoted_at,
            previous_close,
            high,
            low,
            volume,
            _label(meta.get("shortName") or meta.get("longName")),
            _label(meta.get("currency")),
        )
    except (
        KeyError,
        IndexError,
        TypeError,
        AttributeError,
        ValueError,
        OSError,
        OverflowError,
    ):
        raise QuoteError("行情响应不完整或格式异常") from None


def fetch_quote(symbol: str, *, session=None, now: datetime | None = None) -> Quote:
    client = session or requests.Session(impersonate="chrome")
    try:
        for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
            try:
                response = client.get(
                    f"https://{host}/v8/finance/chart/{urlquote(symbol, safe='')}",
                    params={"range": "1d", "interval": "1m"},
                    timeout=15,
                )
                response.raise_for_status()
                return parse_quote(response.json(), symbol, now=now)
            except (RequestException, ValueError, QuoteError):
                continue
    finally:
        if session is None:
            client.close()
    raise QuoteError("行情暂不可用（请求失败或返回数据无效）")


def collect_quotes(
    tickers: tuple[tuple[str, str], ...],
    *,
    fetcher: Callable[[str], Quote] = fetch_quote,
) -> tuple[QuoteResult, ...]:
    results = []
    for name, symbol in tickers:
        try:
            results.append(QuoteResult(name, symbol, fetcher(symbol)))
        except QuoteError:
            results.append(QuoteResult(name, symbol, error="行情暂不可用"))
    return tuple(results)


def collect_configured_quotes() -> tuple[QuoteResult, ...]:
    return collect_quotes(FUTURES_SETTINGS.tickers)


def _formatted(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "暂缺"
    return f"{value:+,.2f}" if signed else f"{value:,.2f}"


def render_quote_report(
    results: tuple[QuoteResult, ...],
    now: datetime,
    max_age_minutes: int = 120,
) -> str:
    if now.tzinfo is None:
        raise ValueError("Report time must be timezone-aware")
    lines = [
        "# 纳指100期货与全球行情晚报",
        f"生成时间：{now.astimezone(APP_TIMEZONE):%Y-%m-%d %H:%M:%S}（北京时间）",
        "数据来源：Yahoo Finance 延迟行情；以下时间均为北京时间。",
        "NQ=F 为 E-mini 纳指100期货滚动报价，具体合约以数据源名称为准。",
        "涨跌按数据源参考前收计算；参考前收不等同于交易所结算价。",
    ]
    if not any(result.symbol == "NQ=F" and result.quote for result in results):
        lines.append("\n⚠️ 主标的纳指100期货暂不可用，不能据其他标的推断其价格。")
    for result in results:
        lines.append(f"\n## {result.name}（{result.symbol}）")
        item = result.quote
        if item is None:
            lines.append("⚠️ 行情暂不可用，本项未填充价格。")
            continue
        unit = {"GC=F": "美元/盎司", "CL=F": "美元/桶"}.get(result.symbol, "点")
        lines.append(f"最新报价：**{item.price:,.2f} {unit}**")
        if item.contract_name:
            lines.append(f"数据源名称：{item.contract_name}")
        lines.append(
            f"报价时间：{item.quoted_at.astimezone(APP_TIMEZONE):%Y-%m-%d %H:%M:%S}"
        )
        if now - item.quoted_at > timedelta(minutes=max_age_minutes):
            lines.append("⚠️ 报价较旧，可能休市或数据延迟；以上为最后可得报价。")
        lines.append(f"参考前收：{_formatted(item.previous_close)}")
        percent = (
            "暂缺" if item.change_percent is None else f"{item.change_percent:+.2f}%"
        )
        lines.append(f"较参考前收：{_formatted(item.change, signed=True)} / {percent}")
        lines.append(f"日内低 / 高：{_formatted(item.low)} / {_formatted(item.high)}")
        volume = "暂缺" if item.volume is None else f"{item.volume:,.0f}"
        lines.append(f"数据源成交量：{volume}")
    lines.append("\n价格可能延迟，期货滚动换月会影响可比性；本报用于行情浏览。")
    return "\n\n".join(lines) + "\n"
