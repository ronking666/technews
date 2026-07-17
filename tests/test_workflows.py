from pathlib import Path

WORKFLOWS = Path(".github/workflows")


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_news_schedule_is_0427_shanghai():
    text = workflow("daily_news.yml")
    assert "cron: '27 4 * * *'" in text
    assert "timezone: 'Asia/Shanghai'" in text


def test_finance_schedule_tracks_new_york_close():
    text = workflow("daily_finance.yml")
    assert "cron: '47 16 * * *'" in text
    assert "timezone: 'America/New_York'" in text


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
