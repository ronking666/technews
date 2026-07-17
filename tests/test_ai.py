from unittest.mock import Mock

import pytest
import requests


def ai_settings(max_input_chars=20):
    from technews.settings import AiSettings

    return AiSettings(
        enabled=True,
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        thinking=False,
        max_input_chars=max_input_chars,
        max_output_tokens=500,
        timeout_seconds=60,
    )


def test_generate_summary_uses_v4_flash_without_thinking():
    from technews.ai import generate_summary

    response = Mock()
    response.json.return_value = {
        "choices": [{"message": {"content": "  三条中文摘要  "}}]
    }
    post = Mock(return_value=response)

    summary = generate_summary(
        "deepseek-secret",
        "news",
        "x" * 100,
        settings=ai_settings(),
        post=post,
    )

    assert summary == "三条中文摘要"
    url = post.call_args.args[0]
    kwargs = post.call_args.kwargs
    assert url == "https://api.deepseek.com/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer deepseek-secret"
    assert kwargs["json"]["model"] == "deepseek-v4-flash"
    assert kwargs["json"]["thinking"] == {"type": "disabled"}
    assert "x" * 21 not in kwargs["json"]["messages"][1]["content"]


def test_configured_summary_skips_missing_key():
    from technews.ai import configured_summary

    assert configured_summary("news", "content", api_key="") is None


def test_generate_summary_hides_key_on_request_failure():
    from technews.ai import SummaryError, generate_summary

    def failing_post(*args, **kwargs):
        raise requests.RequestException("upstream leaked detail")

    with pytest.raises(SummaryError) as error:
        generate_summary(
            "deepseek-secret",
            "finance",
            "content",
            settings=ai_settings(),
            post=failing_post,
        )

    assert "deepseek-secret" not in str(error.value)
    assert "upstream" not in str(error.value)


def test_prepend_summary_adds_disclaimer():
    from technews.ai import prepend_summary

    report = prepend_summary("## 原始报告", "重点一\n重点二")

    assert report.startswith("## 🤖 DeepSeek AI 摘要")
    assert "仅供快速浏览" in report
    assert report.endswith("## 原始报告")


@pytest.mark.parametrize("report_kind", ("news", "finance"))
def test_summary_prompt_requires_mobile_markdown_bullets(report_kind):
    from technews.ai import generate_summary

    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": "- 摘要"}}]}
    post = Mock(return_value=response)

    generate_summary(
        "deepseek-secret",
        report_kind,
        "report content",
        settings=ai_settings(),
        post=post,
    )

    system_prompt = post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "Markdown 项目符号" in system_prompt
    assert "不要输出标题" in system_prompt
