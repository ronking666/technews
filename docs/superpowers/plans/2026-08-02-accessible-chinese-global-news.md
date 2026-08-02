# Accessible Chinese Global News Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把刚新增的六个英文科技 RSS 替换为六个中文、国内文章页可直接访问且仍覆盖全球科技的 RSS。

**Architecture:** 只调整 `config.toml` 的第四至第九个新闻来源，继续复用现有 RSS 解析、去重、高亮和推送数据流。离线测试锁定前三个原始来源不变以及六个中文替代源；真实网络检查验证中文标题和文章页 HTTP 200，不进入 CI。

**Tech Stack:** Python 3.12+、TOML、requests、pytest、Ruff

## Global Constraints

- IT之家、少数派、爱范儿的名称、URL 和顺序保持不变。
- 只替换上一轮新增的六个英文来源。
- 替代来源为雷峰网、极客公园、InfoQ中文、Solidot、36氪、钛媒体。
- 不修改 `items_per_source`、去重、关键词、AI 摘要、推送时间或工作流。
- 不增加翻译 API、依赖、Secret、权限或 Server酱发送次数。
- 不手动运行科技或财经早报。

---

### Task 1: 用中文可访问来源替换英文来源

**Files:**
- Modify: `tests/test_config.py`
- Modify: `config.toml`

**Interfaces:**
- Consumes: `load_settings() -> AppSettings`
- Produces: `AppSettings.news.sources` 中九个按配置顺序排列的 `(name, url)` 元组

- [ ] **Step 1: Change the expected source behavior first**

把 `test_default_news_sources_preserve_existing_and_add_global_coverage` 重命名为
`test_default_news_sources_are_chinese_and_preserve_originals`，保留前三个来源断言，
把 `sources[3:]` 的预期改为：

```python
assert sources[3:] == (
    ("雷峰网", "https://www.leiphone.com/feed"),
    ("极客公园", "https://www.geekpark.net/rss"),
    ("InfoQ中文", "https://www.infoq.cn/feed"),
    ("Solidot", "https://www.solidot.org/index.rss"),
    ("36氪", "https://36kr.com/feed"),
    ("钛媒体", "https://www.tmtpost.com/rss.xml"),
)
```

- [ ] **Step 2: Run the focused test to verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_config.py::test_default_news_sources_are_chinese_and_preserve_originals -q
```

Expected: FAIL because the loaded fourth source is `Hacker News 热门`, not `雷峰网`.

- [ ] **Step 3: Replace only the six appended source tables**

在 `config.toml` 中保留前三个 `[[news.sources]]` 原文不变，用以下配置替换后六个表：

```toml
[[news.sources]]
name = "雷峰网"
url = "https://www.leiphone.com/feed"

[[news.sources]]
name = "极客公园"
url = "https://www.geekpark.net/rss"

[[news.sources]]
name = "InfoQ中文"
url = "https://www.infoq.cn/feed"

[[news.sources]]
name = "Solidot"
url = "https://www.solidot.org/index.rss"

[[news.sources]]
name = "36氪"
url = "https://36kr.com/feed"

[[news.sources]]
name = "钛媒体"
url = "https://www.tmtpost.com/rss.xml"
```

- [ ] **Step 4: Run focused tests to verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_config.py tests\test_rss.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the replacement**

```powershell
git add config.toml tests\test_config.py
git commit -m "fix: use accessible Chinese technology sources"
```

---

### Task 2: 文档、真实抓取与发布

**Files:**
- Modify: `README.md`
- Verify: all changed files and the nine configured sources

**Interfaces:**
- Documents: 中文可访问、仍覆盖全球科技的默认来源组合

- [ ] **Step 1: Update README**

把“全球科技覆盖”说明改为“通过中文媒体覆盖全球科技动态”，并把配置来源清单中的
六个英文来源替换为雷峰网、极客公园、InfoQ中文、Solidot、36氪和钛媒体。

- [ ] **Step 2: Run live RSS and article checks without sending**

使用 `collect_configured_news(create_retrying_session())` 抓取九个来源，每个结果必须
至少包含一条新闻。对 `results[3:]`：

1. 每个来源第一条标题必须匹配 `[\u4e00-\u9fff]`。
2. 使用同一 session GET 第一条链接，响应状态必须为 200。
3. `render_news_report(results)` 字符数不得超过 `AI_SETTINGS.max_input_chars`。

命令不得调用 `main.run`、`configured_summary` 或 `send_to_serverchan`。

- [ ] **Step 3: Run complete offline verification**

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m compileall -q main.py finance.py technews
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 4: Run repository safety checks**

确认 `.github/workflows`、依赖文件、通知和 AI 文件相对 `origin/main` 无差异；扫描疑似
SendKey、DeepSeek Key 和 GitHub token；确认工作树干净。

- [ ] **Step 5: Commit documentation**

```powershell
git add README.md
git commit -m "docs: describe Chinese global news coverage"
```

- [ ] **Step 6: Review, publish, and confirm**

对 `origin/main...HEAD` 做独立只读审查。修复 Critical/Important 问题后重新运行全部
验证，推送 `HEAD:main`，等待 push 触发的 Tests 工作流成功。确认本地 HEAD 与
`origin/main` 一致，不手动触发任何早报工作流。
