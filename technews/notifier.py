from collections.abc import Callable
from typing import Any

import requests

from technews.config import REQUEST_TIMEOUT


class NotificationError(RuntimeError):
    """A credential-safe notification failure."""


def send_to_serverchan(
    sendkey: str,
    title: str,
    content: str,
    post: Callable[..., Any] = requests.post,
) -> None:
    """Send one ServerChan message or raise a credential-safe error."""
    if not sendkey or not sendkey.strip():
        raise NotificationError("SERVERCHAN_SENDKEY is missing")

    try:
        response = post(
            f"https://sctapi.ftqq.com/{sendkey}.send",
            data={"title": title, "desp": content},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        raise NotificationError("ServerChan request failed") from None

    if not isinstance(result, dict) or str(result.get("code")) != "0":
        raise NotificationError("ServerChan rejected the message")
