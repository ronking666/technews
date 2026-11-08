"""Check daily delivery receipts before running an externally triggered report."""

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


class DeliveryGuardError(RuntimeError):
    """A receipt lookup failed; sending with an unknown state is unsafe."""


def prepare_delivery(
    report: str,
    repository: str,
    token: str,
    default_branch: str,
    *,
    now: datetime | None = None,
    opener=None,
) -> tuple[bool, str]:
    if report not in ("news", "finance"):
        raise DeliveryGuardError("Unknown report type")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise DeliveryGuardError("Missing or invalid repository")
    if not token or not default_branch:
        raise DeliveryGuardError("Missing GitHub receipt-check configuration")

    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise DeliveryGuardError("Receipt date requires a timezone-aware time")
    local = current.astimezone(SHANGHAI)
    # Jobs have a 10-minute timeout; leave 15 minutes before the date changes.
    if local.hour == 23 and local.minute >= 45:
        raise DeliveryGuardError("临近北京时间零点，本次停止发送，请次日重试。")
    day = local.date().isoformat()
    name = f"technews-sent-{report}-{day}"
    open_request = opener or urlopen

    try:
        for page in range(1, 11):
            query = urlencode({"name": name, "per_page": 100, "page": page})
            request = Request(
                f"https://api.github.com/repos/{repository}/actions/artifacts?{query}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2026-03-10",
                    "User-Agent": "technews-delivery-guard",
                },
            )
            with open_request(request, timeout=15) as response:
                payload = json.load(response)
            if (
                not isinstance(payload, dict)
                or not isinstance(payload.get("artifacts"), list)
                or type(payload.get("total_count")) is not int
                or payload["total_count"] < 0
            ):
                raise DeliveryGuardError("Invalid GitHub receipt response")
            for artifact in payload["artifacts"]:
                if not isinstance(artifact, dict):
                    raise DeliveryGuardError("Invalid GitHub receipt metadata")
                if artifact.get("name") != name or artifact.get("expired") is True:
                    continue
                source = artifact.get("workflow_run")
                if (
                    artifact.get("expired") is not False
                    or not isinstance(source, dict)
                    or not source.get("repository_id")
                    or not source.get("head_repository_id")
                    or not isinstance(source.get("head_branch"), str)
                ):
                    raise DeliveryGuardError("Incomplete GitHub receipt metadata")
                if (
                    source["head_branch"] == default_branch
                    and source["head_repository_id"] == source["repository_id"]
                ):
                    return False, name
            if page * 100 >= payload["total_count"]:
                return True, name
    except (OSError, ValueError) as error:
        # HTTP exceptions can contain response text; never print their details.
        raise DeliveryGuardError("GitHub receipt lookup failed") from error
    raise DeliveryGuardError("Too many daily receipts to check safely")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", choices=("news", "finance"))
    args = parser.parse_args(argv)
    now = datetime.now(UTC)
    try:
        should_send, name = prepare_delivery(
            args.report,
            os.environ.get("GITHUB_REPOSITORY", ""),
            os.environ.get("GITHUB_TOKEN", ""),
            os.environ.get("REPORT_DEFAULT_BRANCH", ""),
            now=now,
        )
        if should_send:
            path = Path("delivery-receipts/sent.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "report": args.report,
                        "date": now.astimezone(SHANGHAI).date().isoformat(),
                        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"should_send={str(should_send).lower()}\n")
            output.write(f"receipt_name={name}\n")
    except DeliveryGuardError as error:
        print(f"检查当天发送记录失败，本次停止发送：{error}")
        return 1
    except (OSError, KeyError):
        print("检查当天发送记录失败，本次停止发送，请检查 GitHub API 与权限。")
        return 1
    message = "当天尚未发送，开始处理" if should_send else "当天已发送，跳过"
    print(
        f"[北京时间 {now.astimezone(SHANGHAI):%Y-%m-%d %H:%M:%S}] {args.report}: {message}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
