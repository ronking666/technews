# Global Technology News Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改现有三个 RSS 来源和其他新闻配置的前提下，追加六个可被现有解析器读取的全球科技新闻来源。

**Architecture:** 继续使用 `config.toml` 中的 `[[news.sources]]` 列表以及现有 `fetch_news_source` 数据流，不新增解析器、依赖或网络权限。配置测试把加载后的来源元组作为用户可见契约，真实网络检查只作为发布前 smoke test，不进入离线 CI。

**Tech Stack:** Python 3.12+、TOML、requests、pytest、Ruff

## Global Constraints

- IT之家、少数派、爱范儿的名称、URL 和顺序保持不变。
- `items_per_source = 8`、去重开关、关键词、推送时间和工作流均不修改。
- 只追加 Hacker News、Ars Technica、TechCrunch AI、MIT Technology Review AI、OpenAI 官方和 Google AI 官方六个来源。
- 不增加依赖、Secret、工作流权限或 Server酱发送次数。
- 不执行真实 Server酱或 DeepSeek 请求。

---

### Task 1: 追加全球科技 RSS 来源

**Files:**
- Modify: `tests/test_config.py`
- Modify: `config.toml`

**Interfaces:**
- Consumes: `load_settings() -> AppSettings`
- Produces: `AppSettings.news.sources` 中九个按配置顺序排列的 `(name, url)` 元组

- [ ] **Step 1: Write the failing configuration behavior test**

在 `tests/test_config.py` 增加：

```python
def test_default_news_sources_preserve_existing_and_add_global_coverage():
    from technews.settings import load_settings

    sources = load_settings().news.sources

    assert sources[:3] == (
        ("IT之家", "https://www.ithome.com/rss/"),
        ("少数派", "https://sspai.com/feed"),
        ("爱范儿", "https://www.ifanr.com/feed"),
    )
    assert sources[3:] == (
        ("Hacker News 热门", "https://hnrss.org/frontpage"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        (
            "TechCrunch AI",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
        ),
        (
            "MIT Technology Review AI",
            "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        ),
        ("OpenAI 官方动态", "https://openai.com/news/rss.xml"),
        ("Google AI 官方动态", "https://blog.google/technology/ai/rss/"),
    )
```

`load_settings` 校验但不重写来源 URL，因此预期值精确保留 `config.toml` 中的末尾 `/`。

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_config.py::test_default_news_sources_preserve_existing_and_add_global_coverage -q
```

Expected: FAIL because `sources[3:]` is empty.

- [ ] **Step 3: Append the six source tables**

在 `config.toml` 的爱范儿来源之后追加：

```toml
[[news.sources]]
name = "Hacker News 热门"
url = "https://hnrss.org/frontpage"

[[news.sources]]
name = "Ars Technica"
url = "https://feeds.arstechnica.com/arstechnica/index"

[[news.sources]]
name = "TechCrunch AI"
url = "https://techcrunch.com/category/artificial-intelligence/feed/"

[[news.sources]]
name = "MIT Technology Review AI"
url = "https://www.technologyreview.com/topic/artificial-intelligence/feed/"

[[news.sources]]
name = "OpenAI 官方动态"
url = "https://openai.com/news/rss.xml"

[[news.sources]]
name = "Google AI 官方动态"
url = "https://blog.google/technology/ai/rss/"
```

- [ ] **Step 4: Run focused tests to verify GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_config.py tests\test_rss.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the source expansion**

```powershell
git add config.toml tests\test_config.py
git commit -m "feat: add global technology news sources"
```

---

### Task 2: 文档与发布前验证

**Files:**
- Modify: `README.md`
- Verify: `config.toml`, all tests and six remote RSS endpoints

**Interfaces:**
- Documents: the global RSS source coverage and existing failure isolation

- [ ] **Step 1: Update README coverage description**

在“功能亮点”增加一行，说明报告同时覆盖中文科技媒体、全球开发者社区、海外专业科技媒体和 OpenAI/Google 官方动态。

- [ ] **Step 2: Run offline verification**

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m compileall -q main.py finance.py technews
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 3: Run live RSS smoke test without sending**

使用 `create_retrying_session()` 和 `fetch_news_source(..., limit=8)` 读取六个新增 URL。
断言六个结果均没有错误且至少有一条新闻；把九源报告传入 `render_news_report`，
断言字符数不超过 `AI_SETTINGS.max_input_chars`。该命令不得调用 `main.run`、
`send_to_serverchan` 或 `configured_summary`。

- [ ] **Step 4: Verify repository safety**

确认 `.github/workflows` 无差异，扫描疑似 SendKey、DeepSeek Key 和 GitHub token，
并确认工作树只包含本任务文件。

- [ ] **Step 5: Commit documentation**

```powershell
git add README.md
git commit -m "docs: describe global technology coverage"
```

- [ ] **Step 6: Review, publish, and confirm CI**

对 `origin/main...HEAD` 做独立只读审查；修复 Critical/Important 问题后重新运行全部
验证。推送 `HEAD:main`，等待 push 触发的 Tests 工作流成功，并确认本地 HEAD、
`origin/main` 和远端默认分支一致。不手动运行任何早报工作流。
