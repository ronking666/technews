from datetime import date

import pytest
import requests


class Response:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_fetch_fred_closes_parses_values_and_skips_missing_rows():
    from technews.fred import FRED_CSV_URL, fetch_fred_closes

    def get(url, **kwargs):
        assert url == FRED_CSV_URL
        assert kwargs["params"] == {
            "id": "NASDAQ100",
            "cosd": "2026-07-23",
            "coed": "2026-07-27",
        }
        return Response(
            "observation_date,NASDAQ100\n"
            "2026-07-23,28454.81\n"
            "2026-07-24,28128.34\n"
            "2026-07-27,.\n"
        )

    result = fetch_fred_closes(
        "NASDAQ100",
        date(2026, 7, 23),
        date(2026, 7, 27),
        get=get,
    )

    assert result == {
        date(2026, 7, 23): 28454.81,
        date(2026, 7, 24): 28128.34,
    }


@pytest.mark.parametrize(
    "content",
    (
        "date,value\n2026-07-24,28128.34\n",
        "observation_date,NASDAQ100\n2026-07-24,.\n",
        "observation_date,NASDAQ100\ninvalid,not-a-number\n",
    ),
)
def test_fetch_fred_closes_rejects_invalid_or_empty_data(content):
    from technews.fred import MarketDataError, fetch_fred_closes

    with pytest.raises(MarketDataError) as error:
        fetch_fred_closes(
            "NASDAQ100",
            date(2026, 7, 23),
            date(2026, 7, 27),
            get=lambda *args, **kwargs: Response(content),
        )

    assert content not in str(error.value)


def test_fetch_fred_closes_hides_upstream_request_details():
    from technews.fred import MarketDataError, fetch_fred_closes

    def failing_get(*args, **kwargs):
        raise requests.RequestException("upstream secret detail")

    with pytest.raises(MarketDataError) as error:
        fetch_fred_closes(
            "NASDAQ100",
            date(2026, 7, 23),
            date(2026, 7, 27),
            get=failing_get,
        )

    assert "upstream" not in str(error.value)
    assert "secret" not in str(error.value)
