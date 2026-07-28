from datetime import date


def test_expected_nasdaq_sessions_excludes_weekends_and_standard_holidays():
    from technews.market_calendar import expected_nasdaq_sessions

    assert expected_nasdaq_sessions(date(2026, 7, 2), date(2026, 7, 7)) == {
        date(2026, 7, 2),
        date(2026, 7, 6),
    }


def test_expected_nasdaq_sessions_excludes_good_friday():
    from technews.market_calendar import expected_nasdaq_sessions

    assert expected_nasdaq_sessions(date(2026, 4, 2), date(2026, 4, 7)) == {
        date(2026, 4, 2),
        date(2026, 4, 6),
    }
