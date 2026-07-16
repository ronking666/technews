import os
from collections.abc import Callable
from datetime import datetime

from technews.config import APP_TIMEZONE
from technews.market import (
    MarketResult,
    collect_configured_markets,
    render_market_report,
)
from technews.notifier import NotificationError, send_to_serverchan


def _shanghai_time(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(APP_TIMEZONE)
    if now.tzinfo is None:
        return now.replace(tzinfo=APP_TIMEZONE)
    return now.astimezone(APP_TIMEZONE)


def run(
    sendkey: str,
    now: datetime | None = None,
    notifier: Callable[[str, str, str], None] = send_to_serverchan,
    results: tuple[MarketResult, ...] | None = None,
) -> int:
    """Build and send the finance report, returning a process exit code."""
    if not sendkey or not sendkey.strip():
        print("错误：未配置 SERVERCHAN_SENDKEY。")
        return 2

    report_time = _shanghai_time(now)
    if results is None:
        results = collect_configured_markets()

    successful_markets = sum(result.error is None for result in results)
    content = render_market_report(results)
    title = f"📊 每日财经与金属行情早报 ({report_time:%Y年%m月%d日})"

    try:
        notifier(sendkey, title, content)
    except NotificationError as error:
        print(f"推送失败：{error}")
        return 1

    if successful_markets == 0:
        print("所有财经行情均获取失败，已发送失败摘要。")
        return 1

    failed_markets = len(results) - successful_markets
    print(f"财经行情推送成功：{successful_markets} 个标的成功，{failed_markets} 个标的失败。")
    return 0


def main() -> int:
    return run(os.environ.get("SERVERCHAN_SENDKEY", ""))


if __name__ == "__main__":
    raise SystemExit(main())
