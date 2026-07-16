import os
from collections.abc import Callable
from datetime import datetime

import requests

from technews.config import APP_TIMEZONE
from technews.http import create_retrying_session
from technews.notifier import NotificationError, send_to_serverchan
from technews.rss import (
    NewsSourceResult,
    collect_configured_news,
    render_news_report,
)


def _shanghai_time(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(APP_TIMEZONE)
    if now.tzinfo is None:
        return now.replace(tzinfo=APP_TIMEZONE)
    return now.astimezone(APP_TIMEZONE)


def run(
    sendkey: str,
    now: datetime | None = None,
    session: requests.Session | None = None,
    notifier: Callable[[str, str, str], None] = send_to_serverchan,
    results: tuple[NewsSourceResult, ...] | None = None,
) -> int:
    """Build and send the technology report, returning a process exit code."""
    if not sendkey or not sendkey.strip():
        print("错误：未配置 SERVERCHAN_SENDKEY。")
        return 2

    report_time = _shanghai_time(now)
    if results is None:
        results = collect_configured_news(session or create_retrying_session())

    successful_sources = sum(bool(result.items) for result in results)
    content = render_news_report(results)
    title = f"📰 每日科技资讯早报 ({report_time:%Y年%m月%d日})"

    try:
        notifier(sendkey, title, content)
    except NotificationError as error:
        print(f"推送失败：{error}")
        return 1

    if successful_sources == 0:
        print("所有科技资讯源均获取失败，已发送失败摘要。")
        return 1

    failed_sources = len(results) - successful_sources
    print(
        f"科技资讯推送成功：{successful_sources} 个源成功，{failed_sources} 个源失败。"
    )
    return 0


def main() -> int:
    return run(os.environ.get("SERVERCHAN_SENDKEY", ""))


if __name__ == "__main__":
    raise SystemExit(main())
