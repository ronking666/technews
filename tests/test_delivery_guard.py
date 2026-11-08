import io
import json
from contextlib import nullcontext
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

NOW = datetime(2026, 11, 3, 22, 40, tzinfo=UTC)
REPOSITORY = "ronking666/technews"


@pytest.fixture
def fixed_clock(monkeypatch):
    from technews import delivery_guard

    class Clock:
        @staticmethod
        def now(tz):
            return NOW

    monkeypatch.setattr(delivery_guard, "datetime", Clock)


def receipt(name="technews-sent-news-2026-11-04", **changes):
    value = {
        "id": 100,
        "name": name,
        "expired": False,
        "workflow_run": {
            "id": 123,
            "repository_id": 1169870903,
            "head_repository_id": 1169870903,
            "head_branch": "main",
        },
    }
    value.update(changes)
    return value


def api_page(artifacts, total=None):
    return {
        "artifacts": artifacts,
        "total_count": len(artifacts) if total is None else total,
    }


def opener_for(payload):
    def open_request(request, timeout):
        assert timeout == 15
        assert request.get_header("Authorization") == "Bearer test-token"
        url = urlsplit(request.full_url)
        assert url.scheme == "https"
        assert url.netloc == "api.github.com"
        assert url.path == "/repos/ronking666/technews/actions/artifacts"
        assert parse_qs(url.query)["name"] == ["technews-sent-news-2026-11-04"]
        return nullcontext(io.BytesIO(json.dumps(payload).encode()))

    return open_request


def test_no_receipt_allows_delivery_using_beijing_date():
    from technews.delivery_guard import prepare_delivery

    assert prepare_delivery(
        "news",
        REPOSITORY,
        "test-token",
        "main",
        now=NOW,
        opener=opener_for(api_page([])),
    ) == (True, "technews-sent-news-2026-11-04")


def test_successful_receipt_suppresses_same_day_delivery():
    from technews.delivery_guard import prepare_delivery

    assert prepare_delivery(
        "news",
        REPOSITORY,
        "test-token",
        "main",
        now=NOW,
        opener=opener_for(api_page([receipt()])),
    ) == (False, "technews-sent-news-2026-11-04")


@pytest.mark.parametrize(
    "existing",
    [
        receipt(expired=True),
        receipt(name="technews-sent-news-2026-11-03"),
        receipt(name="technews-sent-finance-2026-11-04"),
        receipt(
            workflow_run={
                "repository_id": 1169870903,
                "head_repository_id": 1169870903,
                "head_branch": "feature/test",
            }
        ),
        receipt(
            workflow_run={
                "repository_id": 1169870903,
                "head_repository_id": 999,
                "head_branch": "main",
            }
        ),
    ],
)
def test_expired_foreign_or_other_report_receipts_do_not_block(existing):
    from technews.delivery_guard import prepare_delivery

    should_send, _ = prepare_delivery(
        "news",
        REPOSITORY,
        "test-token",
        "main",
        now=NOW,
        opener=opener_for(api_page([existing])),
    )
    assert should_send is True


def test_finance_uses_its_own_receipt_name():
    from technews.delivery_guard import prepare_delivery

    def open_request(request, timeout):
        assert parse_qs(urlsplit(request.full_url).query)["name"] == [
            "technews-sent-finance-2026-11-04"
        ]
        return nullcontext(io.BytesIO(b'{"artifacts": [], "total_count": 0}'))

    assert prepare_delivery(
        "finance",
        REPOSITORY,
        "test-token",
        "main",
        now=NOW,
        opener=open_request,
    ) == (True, "technews-sent-finance-2026-11-04")


def test_beijing_midnight_starts_a_new_daily_receipt():
    from technews.delivery_guard import prepare_delivery

    now = datetime(2026, 11, 3, 16, 0, tzinfo=UTC)
    assert prepare_delivery(
        "news",
        REPOSITORY,
        "test-token",
        "main",
        now=now,
        opener=opener_for(api_page([])),
    ) == (True, "technews-sent-news-2026-11-04")


def test_check_finds_receipt_beyond_first_page():
    from technews.delivery_guard import prepare_delivery

    def open_request(request, timeout):
        page = parse_qs(urlsplit(request.full_url).query)["page"]
        data = (
            api_page([receipt(expired=True)] * 100, 101)
            if page == ["1"]
            else (api_page([receipt()], 101))
        )
        return nullcontext(io.BytesIO(json.dumps(data).encode()))

    assert (
        prepare_delivery(
            "news",
            REPOSITORY,
            "test-token",
            "main",
            now=NOW,
            opener=open_request,
        )[0]
        is False
    )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"artifacts": None, "total_count": 0},
        {"artifacts": [], "total_count": "bad"},
        api_page([receipt(workflow_run=None)]),
    ],
)
def test_malformed_receipt_response_stops_delivery(payload):
    from technews.delivery_guard import DeliveryGuardError, prepare_delivery

    with pytest.raises(DeliveryGuardError):
        prepare_delivery(
            "news",
            REPOSITORY,
            "test-token",
            "main",
            now=NOW,
            opener=opener_for(payload),
        )


def test_late_night_run_stops_before_it_can_cross_delivery_dates():
    from technews.delivery_guard import DeliveryGuardError, prepare_delivery

    with pytest.raises(DeliveryGuardError, match="零点"):
        prepare_delivery(
            "news",
            REPOSITORY,
            "test-token",
            "main",
            now=datetime(2026, 11, 4, 15, 45, tzinfo=UTC),
            opener=opener_for(api_page([])),
        )


def test_run_before_midnight_safety_window_can_still_send():
    from technews.delivery_guard import prepare_delivery

    assert (
        prepare_delivery(
            "news",
            REPOSITORY,
            "test-token",
            "main",
            now=datetime(2026, 11, 4, 15, 44, 59, tzinfo=UTC),
            opener=opener_for(api_page([])),
        )[0]
        is True
    )


def test_http_error_stops_delivery_without_exposing_token():
    from technews.delivery_guard import DeliveryGuardError, prepare_delivery

    def fail(request, timeout):
        raise HTTPError(request.full_url, 403, "test-token secret", {}, None)

    with pytest.raises(DeliveryGuardError) as result:
        prepare_delivery(
            "news",
            REPOSITORY,
            "test-token",
            "main",
            now=NOW,
            opener=fail,
        )
    assert "test-token" not in str(result.value)


def test_command_writes_outputs_and_secret_free_receipt(
    tmp_path, monkeypatch, fixed_clock
):
    from technews import delivery_guard

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("REPORT_DEFAULT_BRANCH", "main")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    output = tmp_path / "outputs.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        delivery_guard,
        "urlopen",
        lambda *args, **kwargs: nullcontext(
            io.BytesIO(b'{"artifacts": [], "total_count": 0}')
        ),
    )

    assert delivery_guard.main(["news"]) == 0
    text = output.read_text(encoding="utf-8")
    assert "should_send=true\n" in text
    assert "receipt_name=technews-sent-news-" in text
    contents = (tmp_path / "delivery-receipts" / "sent.json").read_text("utf-8")
    assert "test-token" not in contents
    assert json.loads(contents)["report"] == "news"
    assert json.loads(contents)["run_id"] == "123"


def test_command_error_creates_no_allow_output_or_receipt(
    tmp_path, monkeypatch, capsys, fixed_clock
):
    from technews import delivery_guard

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("REPORT_DEFAULT_BRANCH", "main")
    output = tmp_path / "outputs.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))

    def fail(*args, **kwargs):
        raise TimeoutError("test-token secret")

    monkeypatch.setattr(delivery_guard, "urlopen", fail)
    assert delivery_guard.main(["news"]) == 1
    assert not output.exists()
    assert not (tmp_path / "delivery-receipts" / "sent.json").exists()
    assert "test-token" not in capsys.readouterr().out
