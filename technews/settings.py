import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class ConfigError(ValueError):
    """Raised when the user-facing TOML configuration is invalid."""


@dataclass(frozen=True)
class NewsSettings:
    items_per_source: int
    deduplicate: bool
    keywords: tuple[str, ...]
    sources: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class FinanceSettings:
    history_period: str
    trend_windows: tuple[int, ...]
    range_days: int
    tickers: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class AiSettings:
    enabled: bool
    base_url: str
    model: str
    thinking: bool
    max_input_chars: int
    max_output_tokens: int
    timeout_seconds: int


@dataclass(frozen=True)
class AppSettings:
    news: NewsSettings
    finance: FinanceSettings
    ai: AiSettings


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigError(f"{name} must be a positive integer")
    return value


def _non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value.strip()


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a table")
    return value


def _named_pairs(value: Any, name: str, value_key: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{name} must contain at least one item")
    pairs = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ConfigError(f"{name}[{index}] must be a table")
        item_name = _non_empty_string(item.get("name"), f"{name}[{index}].name")
        item_value = _non_empty_string(
            item.get(value_key), f"{name}[{index}].{value_key}"
        )
        pairs.append((item_name, item_value))
    return tuple(pairs)


def _http_url(value: Any, name: str) -> str:
    url = _non_empty_string(value, name)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError(f"{name} must be an HTTP URL")
    return url.rstrip("/")


def _deepseek_base_url(value: Any) -> str:
    url = _http_url(value, "ai.base_url")
    if url not in {
        "https://api.deepseek.com",
        "https://api.deepseek.com/v1",
    }:
        raise ConfigError("ai.base_url must use the official DeepSeek API")
    return url


def load_settings(path: Path | None = None) -> AppSettings:
    config_path = path or Path(__file__).resolve().parents[1] / "config.toml"
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        raise ConfigError("Unable to load config.toml") from None

    news_data = _table(data, "news")
    finance_data = _table(data, "finance")
    ai_data = _table(data, "ai")

    sources = _named_pairs(news_data.get("sources"), "news.sources", "url")
    for index, (_, url) in enumerate(sources):
        _http_url(url, f"news.sources[{index}].url")

    keywords_value = news_data.get("keywords")
    if not isinstance(keywords_value, list):
        raise ConfigError("news.keywords must be a list")
    keywords = tuple(
        _non_empty_string(keyword, "news.keywords item") for keyword in keywords_value
    )

    trend_value = finance_data.get("trend_windows")
    if not isinstance(trend_value, list) or not trend_value:
        raise ConfigError("finance.trend_windows must be a non-empty list")
    trend_windows = tuple(
        _positive_int(window, "finance.trend_windows item") for window in trend_value
    )

    model = _non_empty_string(ai_data.get("model"), "ai.model")
    if model not in {"deepseek-v4-flash", "deepseek-v4-pro"}:
        raise ConfigError("ai.model must be a supported DeepSeek V4 model")

    enabled = ai_data.get("enabled")
    thinking = ai_data.get("thinking")
    deduplicate = news_data.get("deduplicate")
    if not isinstance(enabled, bool) or not isinstance(thinking, bool):
        raise ConfigError("AI flags must be boolean")
    if not isinstance(deduplicate, bool):
        raise ConfigError("news.deduplicate must be boolean")

    return AppSettings(
        news=NewsSettings(
            items_per_source=_positive_int(
                news_data.get("items_per_source"), "news.items_per_source"
            ),
            deduplicate=deduplicate,
            keywords=keywords,
            sources=sources,
        ),
        finance=FinanceSettings(
            history_period=_non_empty_string(
                finance_data.get("history_period"), "finance.history_period"
            ),
            trend_windows=trend_windows,
            range_days=_positive_int(
                finance_data.get("range_days"), "finance.range_days"
            ),
            tickers=_named_pairs(
                finance_data.get("tickers"), "finance.tickers", "symbol"
            ),
        ),
        ai=AiSettings(
            enabled=enabled,
            base_url=_deepseek_base_url(ai_data.get("base_url")),
            model=model,
            thinking=thinking,
            max_input_chars=_positive_int(
                ai_data.get("max_input_chars"), "ai.max_input_chars"
            ),
            max_output_tokens=_positive_int(
                ai_data.get("max_output_tokens"), "ai.max_output_tokens"
            ),
            timeout_seconds=_positive_int(
                ai_data.get("timeout_seconds"), "ai.timeout_seconds"
            ),
        ),
    )
