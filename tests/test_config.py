from pathlib import Path
from urllib.parse import urlparse

import pytest


def test_technology_report_has_independent_news_sources():
    from technews.config import RSS_SOURCES

    hosts = {urlparse(url).netloc for _, url in RSS_SOURCES}

    assert len(RSS_SOURCES) >= 3
    assert len(hosts) == len(RSS_SOURCES)


def test_default_news_sources_are_chinese_and_preserve_originals():
    from technews.settings import load_settings

    sources = load_settings().news.sources

    assert sources[:3] == (
        ("IT之家", "https://www.ithome.com/rss/"),
        ("少数派", "https://sspai.com/feed"),
        ("爱范儿", "https://www.ifanr.com/feed"),
    )
    assert sources[3:] == (
        ("雷峰网", "https://www.leiphone.com/feed"),
        ("极客公园", "https://www.geekpark.net/rss"),
        ("InfoQ中文", "https://www.infoq.cn/feed"),
        ("Solidot", "https://www.solidot.org/index.rss"),
        ("36氪", "https://36kr.com/feed"),
        ("钛媒体", "https://www.tmtpost.com/rss.xml"),
    )


def test_default_settings_load_report_enhancements():
    from technews.settings import load_settings

    settings = load_settings()

    assert settings.news.items_per_source == 8
    assert settings.news.deduplicate is True
    assert "DeepSeek" in settings.news.keywords
    assert settings.finance.trend_windows == (5, 20)
    assert settings.finance.range_days == 20
    assert settings.ai.model == "deepseek-v4-flash"
    assert settings.ai.thinking is False


def test_settings_reject_deprecated_deepseek_model(tmp_path):
    from technews.settings import ConfigError, load_settings

    config = (
        "[news]\nitems_per_source=8\ndeduplicate=true\nkeywords=['AI']\n"
        "[[news.sources]]\nname='源'\nurl='https://example.com/rss'\n"
        "[finance]\nhistory_period='3mo'\ntrend_windows=[5]\nrange_days=5\n"
        "[[finance.tickers]]\nname='指数'\nsymbol='IDX'\n"
        "[ai]\nenabled=true\nbase_url='https://api.deepseek.com'\n"
        "model='deepseek-chat'\nthinking=false\nmax_input_chars=1000\n"
        "max_output_tokens=100\ntimeout_seconds=30\n"
    )
    path = tmp_path / "config.toml"
    path.write_text(config, encoding="utf-8")

    with pytest.raises(ConfigError, match="model"):
        load_settings(path)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    (
        (
            'url = "https://www.ithome.com/rss/"',
            'url = "ftp://example.com/rss"',
            "HTTP URL",
        ),
        ("trend_windows = [5, 20]", "trend_windows = [0]", "positive integer"),
        ('name = "IT之家"', 'name = ""', "non-empty string"),
        (
            'base_url = "https://api.deepseek.com"',
            'base_url = "https://example.com"',
            "official DeepSeek API",
        ),
    ),
)
def test_settings_reject_unsafe_or_empty_values(tmp_path, old, new, message):
    from technews.settings import ConfigError, load_settings

    config = Path("config.toml").read_text(encoding="utf-8").replace(old, new, 1)
    path = tmp_path / "config.toml"
    path.write_text(config, encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_settings(path)
