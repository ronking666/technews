"""FRED daily close data used to validate market history."""

import csv
import math
from collections.abc import Callable
from datetime import date
from io import StringIO
from typing import Any

import requests

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_HEADERS = {
    "User-Agent": "technews-daily-report/1.0 (+https://github.com/ronking666/technews)"
}
FRED_TIMEOUT = (5, 20)


class MarketDataError(RuntimeError):
    """Raised when official market history cannot be loaded safely."""


def fetch_fred_closes(
    series_id: str,
    start: date,
    end: date,
    *,
    get: Callable[..., Any] = requests.get,
) -> dict[date, float]:
    """Return finite FRED daily observations keyed by date."""
    try:
        response = get(
            FRED_CSV_URL,
            params={
                "id": series_id,
                "cosd": start.isoformat(),
                "coed": end.isoformat(),
            },
            headers=FRED_HEADERS,
            timeout=FRED_TIMEOUT,
        )
        response.raise_for_status()
        reader = csv.DictReader(StringIO(response.text))
        if (
            not reader.fieldnames
            or "observation_date" not in reader.fieldnames
            or series_id not in reader.fieldnames
        ):
            raise ValueError

        closes = {}
        for row in reader:
            try:
                observed = date.fromisoformat(row["observation_date"])
                value = float(row[series_id])
            except (TypeError, ValueError):
                continue
            if math.isfinite(value):
                closes[observed] = value

        if not closes:
            raise ValueError
        return closes
    except (requests.RequestException, ValueError, csv.Error):
        raise MarketDataError("Official market history is unavailable") from None
