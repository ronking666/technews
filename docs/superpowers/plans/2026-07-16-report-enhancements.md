# Intelligent Report Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加 TOML 配置、新闻去重与关键词高亮、财经趋势和可降级的 DeepSeek V4 中文摘要，同时保持每天两次 Server酱推送。

**Architecture:** `technews/settings.py` 只负责配置；`rss.py` 和 `market.py` 负责确定性增强；`ai.py` 只负责 DeepSeek API 与摘要展示；入口脚本编排这些模块。AI 缺失或失败时跳过摘要，不改变基础报告的成功判定。

**Tech Stack:** Python 3.12、tomllib、requests、pandas/yfinance、pytest、Ruff、DeepSeek OpenAI-compatible Chat Completions

## Global Constraints

- 调度保持北京时间 05:30 与 06:15。
- Server酱仍为每天两条消息。
- DeepSeek 模型固定为 `deepseek-v4-flash`，`thinking.type` 为 `disabled`。
- `DEEPSEEK_API_KEY` 只从环境变量和 GitHub Secret 读取。
- AI 失败不得阻止基础报告发送。
- 不执行真实 Server酱或 DeepSeek 请求。

---

### Task 1: TOML 配置加载

**Files:** Create `config.toml`, `technews/settings.py`; modify `technews/config.py`; test `tests/test_config.py`.

**Interfaces:**
- Produces: `load_settings(path: Path | None = None) -> AppSettings`。
- Produces: `NewsSettings(items_per_source, deduplicate, keywords, sources)`、`FinanceSettings(history_period, trend_windows, range_days, tickers)`、`AiSettings(enabled, base_url, model, thinking, max_input_chars, max_output_tokens, timeout_seconds)`。
- Preserves: `RSS_SOURCES`、`MARKET_TICKERS`、`APP_TIMEZONE`、`REQUEST_TIMEOUT`。

- [ ] Add failing tests for default loading and invalid URL/window/model.
- [ ] Run `python -m pytest tests/test_config.py -q`; expect import or file failures.
- [ ] Implement dataclasses, strict validation, default path, compatibility constants.
- [ ] Run `python -m pytest tests/test_config.py -q`; expect pass.
- [ ] Commit `feat: add configurable report settings`.

---

### Task 2: 新闻去重与关键词高亮

**Files:** Modify `technews/rss.py`; test `tests/test_rss.py` and `tests/test_main.py`.

**Interfaces:**
- Produces: `normalize_news_title(title: str) -> str`。
- Produces: `deduplicate_news(results: tuple[NewsSourceResult, ...]) -> tuple[NewsSourceResult, ...]`。
- Extends: `render_news_report(results, keywords=NEWS_KEYWORDS, deduplicate=NEWS_DEDUPLICATE) -> str`。

- [ ] Add failing tests proving cross-source duplicates appear once, later empty duplicate source is omitted, keywords are case-insensitive and failures remain.
- [ ] Run targeted RSS tests; expect missing functions/signature failure.
- [ ] Implement Unicode NFKC/casefold/alphanumeric key, first-source-wins filtering and `🔥` prefix.
- [ ] Run RSS and main tests; expect pass.
- [ ] Commit `feat: deduplicate and highlight news`.

---

### Task 3: 财经趋势增强

**Files:** Modify `technews/market.py`; test `tests/test_market.py` and `tests/test_finance.py`.

**Interfaces:**
- Extends `MarketResult` with `trend_returns`, `range_window`, `range_low`, `range_high` after existing fields.
- Extends `market_result_from_history(name, symbol, history, trend_windows=TREND_WINDOWS, range_days=RANGE_DAYS)`。
- Fetches `history(period=MARKET_HISTORY_PERIOD, timeout=15, raise_errors=True)`。

- [ ] Add failing tests for 5/20-day returns, 20-day range, insufficient optional history and rendered trend lines.
- [ ] Run targeted market tests; expect missing fields/assertion failure.
- [ ] Implement window returns and range from valid closes; omit unavailable windows without failing the symbol.
- [ ] Run market and finance tests; expect pass.
- [ ] Commit `feat: add finance trend indicators`.

---

### Task 4: DeepSeek V4 摘要与降级

**Files:** Create `technews/ai.py`, `tests/test_ai.py`; modify `main.py`, `finance.py`, their tests.

**Interfaces:**
- Produces: `SummaryError(RuntimeError)`。
- Produces: `generate_summary(api_key, report_kind, content, settings=AI_SETTINGS, post=requests.post) -> str`。
- Produces: `configured_summary(report_kind, content, api_key=None) -> str | None`。
- Produces: `prepend_summary(content: str, summary: str | None) -> str`。
- Extends both `run` functions with injectable `summarizer: Callable[[str, str], str | None]`。

- [ ] Add failing tests for URL/Header/payload, truncation, parsing, missing key skip, safe errors, successful prepend and failure fallback.
- [ ] Run AI and entry tests; expect missing module/signature failures.
- [ ] Implement non-streaming V4 Flash request with thinking disabled and safe response validation.
- [ ] Catch only `SummaryError` in entry scripts, log safe message and continue sending the deterministic report.
- [ ] Run AI, main and finance tests; expect pass.
- [ ] Commit `feat: add optional DeepSeek summaries`.

---

### Task 5: 工作流、文档、全量发布

**Files:** Modify both daily workflows, `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `tests/test_workflows.py`, `tests/test_repository_quality.py`.

**Interfaces:** Both workflows expose optional `DEEPSEEK_API_KEY` from `secrets.DEEPSEEK_API_KEY`; no other permissions or schedules change.

- [ ] Add failing workflow tests for the optional Secret and repository tests for `config.toml`.
- [ ] Add Secret env to both workflows and document configuration, costs, fallback and no-chat key handling.
- [ ] Run `python -m ruff check .`, `python -m ruff format --check .`, `python -m pytest -q`, YAML parsing and `git diff --check`.
- [ ] Verify scheduled workflow diffs contain only the added DeepSeek environment line.
- [ ] Commit `docs: document intelligent report features`.
- [ ] Push `HEAD:main`, update topics with `deepseek`, confirm GitHub Actions success, local/remote SHA equality and clean status.
