from urllib.parse import urlparse

import pytest


def test_technology_report_has_independent_news_sources():
    from technews.config import RSS_SOURCES

    hosts = {urlparse(url).netloc for _, url in RSS_SOURCES}

    assert len(RSS_SOURCES) >= 3
    assert len(hosts) == len(RSS_SOURCES)


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
