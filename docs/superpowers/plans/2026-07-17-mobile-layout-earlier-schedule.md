# Mobile Report Layout and Earlier Schedule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让科技与财经早报在 Server酱手机页面上逐项清晰显示，并通过时区感知调度更早送达。

**Architecture:** 保持采集、去重、趋势计算和通知链路不变，只修改确定性 Markdown 渲染与 AI 输出格式约束；GitHub Actions 使用 IANA 时区直接表达北京时间和纽约时间。财经调度绑定纽约收盘后 47 分钟，自动适配美国夏令时。

**Tech Stack:** Python 3.12、pytest、Markdown、GitHub Actions timezone-aware cron、Ruff

## Global Constraints

- 科技任务目标时间固定为北京时间 04:27。
- 财经任务目标时间固定为纽约时间 16:47，即北京时间夏令时约 04:47、冬令时约 05:47。
- 不修改 RSS 来源、每源条数、行情标的、行情历史范围、重试和 Server酱发送次数。
- 不执行真实 Server酱推送测试。
- 手动 `workflow_dispatch`、最小权限和两个 GitHub Secret 必须保留。

---

### Task 1: 手机优先的报告 Markdown

**Files:**
- Modify: `technews/market.py`
- Modify: `technews/rss.py`
- Modify: `technews/ai.py`
- Test: `tests/test_market.py`
- Test: `tests/test_rss.py`
- Test: `tests/test_ai.py`

**Interfaces:**
- Preserves: `render_market_report(results: tuple[MarketResult, ...]) -> str`
- Preserves: `render_news_report(results, keywords=NEWS_KEYWORDS, deduplicate=NEWS_DEDUPLICATE) -> str`
- Preserves: `generate_summary(api_key, report_kind, content, *, settings=AI_SETTINGS, post=requests.post) -> str`
- Produces: 财经每项指标为独立 `- **标签**：值` 列表项，新闻项目和来源间有空行/分隔线，AI 系统提示要求 Markdown 项目符号。

- [ ] **Step 1: Write failing mobile-layout tests**

在 `tests/test_market.py` 中把趋势渲染断言改为：

```python
assert "- **数据日期**：2026-07-15" in report
assert "- **最新价**：**124.00**" in report
assert "- **当日涨跌**：+1.00（+0.81%）" in report
assert "- **5日趋势**：+4.20%" in report
assert "- **20日趋势**：+19.23%" in report
assert "- **20日区间**：105.00 ～ 124.00" in report
assert " ｜ " not in report
```

在 `tests/test_rss.py` 新增两个来源、每个来源两个条目的测试，并断言：

```python
assert "## 📰 来源一\n\n1. 第一条\n\n2. 第二条" in report
assert "\n\n---\n\n## 📰 来源二" in report
```

在 `tests/test_ai.py` 参数化 `news` 和 `finance` 请求，读取 `post.call_args.kwargs["json"]["messages"][0]["content"]`，断言包含 `Markdown 项目符号` 和 `不要输出标题`。

- [ ] **Step 2: Run tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_market.py tests/test_rss.py tests/test_ai.py -q`

Expected: FAIL because the current finance renderer uses blockquotes and `｜`, news items are compact, and AI prompts do not require Markdown bullets.

- [ ] **Step 3: Implement the minimal finance renderer**

在 `render_market_report` 中为成功标的构造列表：

```python
lines = [
    f"### {emoji} {result.name}",
    "",
    f"- **数据日期**：{result.data_date:%Y-%m-%d}",
    f"- **最新价**：**{result.current:.2f}**",
    f"- **当日涨跌**：{sign}{change:.2f}（{sign}{pct_change:.2f}%）",
]
for window, value in result.trend_returns:
    lines.append(f"- **{window}日趋势**：{_signed_percentage(value)}")
if result.range_window and result.range_low is not None and result.range_high is not None:
    lines.append(
        f"- **{result.range_window}日区间**："
        f"{result.range_low:.2f} ～ {result.range_high:.2f}"
    )
sections.append("\n".join(lines))
```

- [ ] **Step 4: Implement news spacing and AI bullet instructions**

新闻成功章节使用 `"\n\n".join(lines)`，全部章节使用 `"\n\n---\n\n".join(sections)`。AI 的两个系统提示均明确包含：

```text
请用 3–5 条 Markdown 项目符号输出，每条只表达一个重点，不要输出标题。
```

- [ ] **Step 5: Run targeted tests and commit**

Run: `.venv\Scripts\python.exe -m pytest tests/test_market.py tests/test_rss.py tests/test_ai.py tests/test_main.py tests/test_finance.py -q`

Expected: PASS.

```bash
git add technews/market.py technews/rss.py technews/ai.py tests/test_market.py tests/test_rss.py tests/test_ai.py
git commit -m "feat: improve mobile report readability"
```

---

### Task 2: 时区感知的提前调度与说明

**Files:**
- Modify: `.github/workflows/daily_news.yml`
- Modify: `.github/workflows/daily_finance.yml`
- Modify: `tests/test_workflows.py`
- Modify: `README.md`

**Interfaces:**
- Produces: 新闻 schedule `{cron: '27 4 * * *', timezone: 'Asia/Shanghai'}`。
- Produces: 财经 schedule `{cron: '47 16 * * *', timezone: 'America/New_York'}`。
- Preserves: `workflow_dispatch`、`contents: read`、并发组、超时、依赖缓存、`SERVERCHAN_SENDKEY`、`DEEPSEEK_API_KEY`。

- [ ] **Step 1: Write failing workflow schedule tests**

将 `tests/test_workflows.py` 的旧时间测试替换为：

```python
def test_news_schedule_is_0427_shanghai():
    text = workflow("daily_news.yml")
    assert "cron: '27 4 * * *'" in text
    assert "timezone: 'Asia/Shanghai'" in text


def test_finance_schedule_tracks_new_york_close():
    text = workflow("daily_finance.yml")
    assert "cron: '47 16 * * *'" in text
    assert "timezone: 'America/New_York'" in text
```

- [ ] **Step 2: Run workflow tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_workflows.py -q`

Expected: two schedule tests FAIL against the old fixed UTC expressions.

- [ ] **Step 3: Implement timezone-aware schedules**

新闻工作流：

```yaml
on:
  schedule:
    - cron: '27 4 * * *'
      timezone: 'Asia/Shanghai'
  workflow_dispatch:
```

财经工作流：

```yaml
on:
  schedule:
    - cron: '47 16 * * *'
      timezone: 'America/New_York'
  workflow_dispatch:
```

- [ ] **Step 4: Update README timing and delay explanation**

将推送时间表改为科技 04:27、财经夏令时约 04:47/冬令时约 05:47；说明财经绑定纽约收盘、GitHub `schedule` 可能延迟，时区感知调度保护数据完整性。更新“到点后没有立刻收到消息”的排查文字。

- [ ] **Step 5: Run workflow/repository tests and commit**

Run: `.venv\Scripts\python.exe -m pytest tests/test_workflows.py tests/test_repository_quality.py -q`

Expected: PASS.

```bash
git add .github/workflows/daily_news.yml .github/workflows/daily_finance.yml tests/test_workflows.py README.md
git commit -m "fix: schedule reports earlier with timezones"
```

---

### Task 3: 全量验证与发布

**Files:**
- Verify: all changed files

**Interfaces:**
- Produces: verified `main` publication with no real Server酱 or DeepSeek request.

- [ ] **Step 1: Run the full local verification suite**

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m compileall -q main.py finance.py technews
```

Expected: all commands exit 0.

- [ ] **Step 2: Validate YAML, credentials, diffs, and schedules**

Parse every `.github/workflows/*.yml`, scan tracked files for credential-like values, run `git diff --check`, and verify the only schedule changes are the intended cron/timezone pairs while `workflow_dispatch` remains.

- [ ] **Step 3: Push and verify remote CI**

Push `HEAD:main`, wait for the push CI run to complete successfully, then verify local HEAD equals remote `main` and the working tree is clean. Do not manually dispatch either report workflow.
