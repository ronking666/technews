from unittest.mock import Mock

import pytest
import requests


def successful_response(code=0):
    response = Mock()
    response.json.return_value = {"code": code}
    return response


def test_notifier_accepts_serverchan_success():
    from technews.notifier import send_to_serverchan

    post = Mock(return_value=successful_response())

    send_to_serverchan("secret", "title", "body", post=post)

    post.assert_called_once()
    _, kwargs = post.call_args
    assert kwargs["data"] == {"title": "title", "desp": "body"}
    assert kwargs["timeout"] == (5, 15)


def test_notifier_rejects_empty_sendkey_without_request():
    from technews.notifier import NotificationError, send_to_serverchan

    post = Mock()

    with pytest.raises(NotificationError, match="SERVERCHAN_SENDKEY"):
        send_to_serverchan("  ", "title", "body", post=post)

    post.assert_not_called()


def test_notifier_treats_api_error_as_failure():
    from technews.notifier import NotificationError, send_to_serverchan

    post = Mock(return_value=successful_response(code=1))

    with pytest.raises(NotificationError, match="rejected"):
        send_to_serverchan("secret", "title", "body", post=post)


def test_notifier_hides_sendkey_from_transport_failure():
    from technews.notifier import NotificationError, send_to_serverchan

    def fail(*args, **kwargs):
        raise requests.RequestException("https://sctapi.ftqq.com/secret.send")

    with pytest.raises(NotificationError) as error:
        send_to_serverchan("secret", "title", "body", post=fail)

    assert "secret" not in str(error.value)


def test_notifier_handles_non_json_response_safely():
    from technews.notifier import NotificationError, send_to_serverchan

    response = successful_response()
    response.json.side_effect = ValueError("invalid json at secret")

    with pytest.raises(NotificationError, match="request failed") as error:
        send_to_serverchan("secret", "title", "body", post=Mock(return_value=response))

    assert "secret" not in str(error.value)
