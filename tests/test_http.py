def test_retry_session_retries_only_safe_get_requests():
    from technews.http import create_retrying_session

    adapter = create_retrying_session().get_adapter("https://")

    assert adapter.max_retries.total == 3
    assert adapter.max_retries.allowed_methods == frozenset({"GET"})
    assert set(adapter.max_retries.status_forcelist) == {429, 500, 502, 503, 504}


def test_retry_session_configures_http_and_https():
    from technews.http import create_retrying_session

    session = create_retrying_session()

    assert session.get_adapter("http://").max_retries.total == 3
    assert session.get_adapter("https://").max_retries.total == 3
