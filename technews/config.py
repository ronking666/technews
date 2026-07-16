from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("Asia/Shanghai")
REQUEST_TIMEOUT = (5, 15)

RSS_SOURCES = (
    ("IT之家", "https://www.ithome.com/rss/"),
    ("少数派", "https://sspai.com/feed"),
    ("爱范儿", "https://www.ifanr.com/feed"),
)

MARKET_TICKERS = (
    ("纳斯达克100指数", "^NDX"),
    ("黄金（纽约期金）", "GC=F"),
    ("白银（纽约期银）", "SI=F"),
    ("铜（纽约期铜）", "HG=F"),
    ("铂金（纽约期铂）", "PL=F"),
    ("稀土与战略金属ETF", "REMX"),
)
