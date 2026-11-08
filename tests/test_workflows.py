from pathlib import Path

import yaml

WORKFLOWS = Path(".github/workflows")


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def document(name):
    # BaseLoader preserves the YAML 1.2 `on` key rather than reading it as bool.
    return yaml.load(workflow(name), Loader=yaml.BaseLoader)


def test_native_early_schedules_remain_available_before_external_activation():
    for name, cron, timezone in (
        ("daily_news.yml", "27 4 * * *", "Asia/Shanghai"),
        ("daily_finance.yml", "47 16 * * *", "America/New_York"),
    ):
        config = document(name)
        assert config["on"]["schedule"] == [{"cron": cron, "timezone": timezone}]
        assert "workflow_dispatch" in config["on"]


def test_all_delivery_paths_share_serial_execution_and_receipt_conditions():
    for filename, kind, group in (
        ("daily_news.yml", "news", "daily-tech-news"),
        ("daily_finance.yml", "finance", "daily-finance-report"),
    ):
        config = document(filename)
        assert config["concurrency"] == {
            "group": group,
            "cancel-in-progress": "false",
        }
        assert config["permissions"] == {"contents": "read", "actions": "read"}
        job = next(iter(config["jobs"].values()))
        assert "github.event.repository.default_branch" in job["if"]
        steps = job["steps"]
        guard_index = next(
            i for i, step in enumerate(steps) if step.get("id") == "delivery"
        )
        send_index = next(i for i, step in enumerate(steps) if step.get("id") == "send")
        guard = steps[guard_index]
        assert guard["run"] == f"python -m technews.delivery_guard {kind}"
        assert guard_index < send_index
        for step in steps[guard_index + 1 : send_index + 1]:
            assert step["if"] == "steps.delivery.outputs.should_send == 'true'"
        upload = steps[send_index + 1]
        assert "steps.send.outcome == 'success'" in upload["if"]
        assert upload["uses"].startswith("actions/upload-artifact@")
        assert upload["with"]["name"] == "${{ steps.delivery.outputs.receipt_name }}"
        assert upload["with"]["path"] == "delivery-receipts/sent.json"
        assert upload["with"]["retention-days"] == "7"
        assert upload["with"]["if-no-files-found"] == "error"
        assert "SERVERCHAN_SENDKEY" not in guard["env"]
        assert "GITHUB_TOKEN" not in steps[send_index]["env"]


def test_scheduled_workflows_use_requirements_and_least_privilege():
    for name in ("daily_news.yml", "daily_finance.yml"):
        text = workflow(name)
        assert "permissions:\n  contents: read" in text
        assert "pip install -r requirements.txt" in text
        assert "timeout-minutes: 10" in text
        assert "concurrency:" in text
        assert "cache: 'pip'" in text
        assert "workflow_dispatch:" in text
        assert "DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}" in text


def test_ci_runs_the_complete_test_suite():
    text = workflow("ci.yml")

    assert "pull_request:" in text
    assert "pip install -r requirements-dev.txt" in text
    assert "python -m pytest -q" in text
