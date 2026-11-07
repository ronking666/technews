"""Daily evening futures report; --preview fetches quotes without sending."""

import argparse
import os
from collections.abc import Callable
from datetime import datetime

from technews.config import APP_TIMEZONE, FUTURES_SETTINGS
from technews.notifier import NotificationError, send_to_serverchan
from technews.quotes import (
    QuoteResult,
    collect_configured_quotes,
    render_quote_report,
)


def run(
    sendkey: str,
    now: datetime | None = None,
    notifier: Callable[[str, str, str], None] = send_to_serverchan,
    results: tuple[QuoteResult, ...] | None = None,
) -> int:
    if not sendkey or not sendkey.strip():
        print("错误：未配置 SERVERCHAN_SENDKEY。")
        return 2
    if results is None:
        results = collect_configured_quotes()
    report_time = now or datetime.now(APP_TIMEZONE)
    if report_time.tzinfo is None:
        report_time = report_time.replace(tzinfo=APP_TIMEZONE)
    content = render_quote_report(
        results, report_time, FUTURES_SETTINGS.max_age_minutes
    )
    title = f"📈 纳指100期货晚报 ({report_time.astimezone(APP_TIMEZONE):%Y年%m月%d日})"
    try:
        notifier(sendkey, title, content)
    except NotificationError:
        print("晚报推送失败，请检查 Server酱服务与额度。")
        return 1
    successful = sum(item.quote is not None for item in results)
    if successful == 0:
        print("行情全部获取失败，已发送失败摘要，等待补发。")
        return 1
    if not any(item.symbol == "NQ=F" and item.quote for item in results):
        print("纳指100期货获取失败，已发送可用行情，等待补发主标的。")
        return 1
    print(
        f"期货晚报推送成功：{successful} 项有报价，{len(results) - successful} 项暂缺。"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="只预览，不发送微信")
    args = parser.parse_args(argv)
    if args.preview:
        results = collect_configured_quotes()
        print(
            render_quote_report(
                results, datetime.now(APP_TIMEZONE), FUTURES_SETTINGS.max_age_minutes
            )
        )
        return 0 if any(item.symbol == "NQ=F" and item.quote for item in results) else 1
    return run(os.environ.get("SERVERCHAN_SENDKEY", ""))


if __name__ == "__main__":
    raise SystemExit(main())
