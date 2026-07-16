from urllib.parse import urlparse


def test_technology_report_has_independent_news_sources():
    from technews.config import RSS_SOURCES

    hosts = {urlparse(url).netloc for _, url in RSS_SOURCES}

    assert len(RSS_SOURCES) >= 3
    assert len(hosts) == len(RSS_SOURCES)
