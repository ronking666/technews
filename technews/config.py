from zoneinfo import ZoneInfo

from technews.settings import load_settings

APP_TIMEZONE = ZoneInfo("Asia/Shanghai")
REQUEST_TIMEOUT = (5, 15)

SETTINGS = load_settings()
RSS_SOURCES = SETTINGS.news.sources
NEWS_ITEM_LIMIT = SETTINGS.news.items_per_source
NEWS_DEDUPLICATE = SETTINGS.news.deduplicate
NEWS_KEYWORDS = SETTINGS.news.keywords
MARKET_TICKERS = SETTINGS.finance.tickers
MARKET_HISTORY_PERIOD = SETTINGS.finance.history_period
TREND_WINDOWS = SETTINGS.finance.trend_windows
RANGE_DAYS = SETTINGS.finance.range_days
AI_SETTINGS = SETTINGS.ai
FUTURES_SETTINGS = SETTINGS.futures
