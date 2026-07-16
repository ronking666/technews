from pathlib import Path


WORKFLOWS = Path(".github/workflows")


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_news_schedule_is_0530_shanghai():
    assert "cron: '30 21 * * *'" in workflow("daily_news.yml")


def test_finance_schedule_is_0615_shanghai():
    assert "cron: '15 22 * * *'" in workflow("daily_finance.yml")


def test_scheduled_workflows_use_requirements_and_least_privilege():
    for name in ("daily_news.yml", "daily_finance.yml"):
        text = workflow(name)
        assert "permissions:\n  contents: read" in text
        assert "pip install -r requirements.txt" in text
        assert "timeout-minutes: 10" in text
        assert "concurrency:" in text
        assert "cache: 'pip'" in text


def test_ci_runs_the_complete_test_suite():
    text = workflow("ci.yml")

    assert "pull_request:" in text
    assert "pip install -r requirements-dev.txt" in text
    assert "python -m pytest -q" in text
