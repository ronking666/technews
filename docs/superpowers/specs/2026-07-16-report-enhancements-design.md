# TechNews 智能报告增强设计

## 目标

在保持北京时间 05:30 科技早报与 06:15 财经早报、每天两次 Server酱推送不变的前提下，增加可编辑配置、跨来源新闻去重、关键词高亮、财经趋势指标和可降级的 DeepSeek 中文摘要。

## 方案选择

采用模块化增强方案：TOML 文件负责用户配置；配置加载器负责解析与校验；RSS 和行情模块各自完成确定性增强；独立 AI 模块封装 DeepSeek Chat Completions；入口脚本只负责采集、渲染、可选摘要和推送。

不采用把逻辑直接写进 `main.py`/`finance.py` 的最小改法，因为配置、网络错误和报告渲染会耦合。不采用通用插件平台，因为目前只有一个 AI 服务商和一个通知渠道。

## 配置文件

新增根目录 `config.toml`，包含以下配置：

- `news.items_per_source = 8`：每个 RSS 来源最多保留的新闻数。
- `news.deduplicate = true`：启用跨来源精确去重。
- `news.keywords`：默认关注 AI、人工智能、大模型、DeepSeek、芯片、半导体和机器人。
- `[[news.sources]]`：来源名称与 RSS URL。
- `finance.history_period = "3mo"`：Yahoo Finance 拉取区间。
- `finance.trend_windows = [5, 20]`：显示 5 日和 20 日收益。
- `finance.range_days = 20`：显示最近 20 个有效交易日的高低区间。
- `[[finance.tickers]]`：行情名称与 symbol。
- `ai.enabled = true`：允许在存在 API Key 时调用 AI。
- `ai.base_url = "https://api.deepseek.com"`。
- `ai.model = "deepseek-v4-flash"`。
- `ai.thinking = false`：摘要使用非思考模式，降低延迟和输出成本。
- `ai.max_input_chars = 12000`、`ai.max_output_tokens = 500`、`ai.timeout_seconds = 60`。

新增 `technews/settings.py`，使用 Python 3.12 标准库 `tomllib` 加载配置并返回不可变 dataclass。URL、正整数、趋势窗口、模型名和必要列表均严格校验；配置错误会在工作流启动阶段明确失败。`technews/config.py` 保留现有常量名称作为兼容层。

## 新闻去重与关键词高亮

`technews/rss.py` 增加纯函数新闻增强流程：

1. 标题使用 Unicode 归一化、`casefold`、去标点和压缩空白生成去重键。
2. 按配置文件中的来源顺序遍历，重复新闻只保留第一次出现的版本。
3. 去重导致完全为空的后续来源不显示空章节；真正抓取失败的来源仍显示失败提示。
4. 标题包含任一关键词时，在列表项前加 `🔥`，匹配不区分英文大小写。
5. Markdown 转义和 URL 安全规则保持不变。

去重只作用于渲染结果，不改变原始抓取成功数，因此不会把“内容重复”误判为上游全部失败。

## 财经趋势增强

`MarketResult` 增加以下不可变字段：

- `trend_returns: tuple[tuple[int, float], ...]`：窗口天数与对应百分比收益。
- `range_window: int`：实际参与区间计算的有效交易日数。
- `range_low`、`range_high`：区间最低与最高收盘价。

`market_result_from_history` 继续要求至少两个有效收盘价计算日涨跌。某个趋势窗口只有在数据量大于窗口时才生成；不足不会令整个标的失败。行情请求从 `7d` 改为配置的 `3mo`，以覆盖 20 日趋势。

报告每个成功标的增加“趋势：5日 …｜20日 …”与“20日区间：低点–高点”。失败标的保持原有安全错误文本。

## DeepSeek 中文摘要

新增 `technews/ai.py`：

- 直接使用现有 `requests` 依赖调用 `POST {base_url}/chat/completions`，不增加 OpenAI SDK。
- 使用 `Authorization: Bearer ...`，API Key 只从环境变量 `DEEPSEEK_API_KEY` 读取。
- 请求模型为 `deepseek-v4-flash`，设置 `thinking.type = "disabled"`、`stream = false`。
- 新闻提示词要求输出三条以内的中文重点，不执行或复述输入中的指令。
- 财经提示词要求概括趋势和风险，不给出买卖建议。
- 输入在配置上限处截断，输出去空白并限制展示长度。
- 401、402、429、5xx、超时、无效 JSON 或无内容统一转换成不包含凭据和上游详情的 `SummaryError`。

`main.py` 和 `finance.py` 先生成确定性报告，再尝试生成摘要。成功时在顶部增加 `## 🤖 DeepSeek AI 摘要` 和“仅供快速浏览”提示；失败、禁用或 Key 缺失时发送原始报告。AI 失败不改变工作流退出码。

## 工作流与 Secret

两个正式推送工作流增加：

```yaml
DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

`SERVERCHAN_SENDKEY` 仍是必需项。`DEEPSEEK_API_KEY` 是可选项：未配置时推送照常进行，只是不显示 AI 摘要。用户必须在 GitHub `Settings → Secrets and variables → Actions` 中自行创建 Secret，不在聊天、代码、日志或截图中发送 Key。

## 测试

- 配置：默认 TOML 可加载，错误 URL、空来源、非法趋势窗口和错误 AI 模型会失败。
- 新闻：跨来源重复只保留一次，关键词大小写不敏感，失败来源仍显示。
- 财经：5 日/20 日收益与 20 日区间计算正确，数据不足时安全省略趋势。
- AI：请求 URL、Header、模型、非思考模式、截断和响应解析正确；缺 Key 不请求；所有外部失败不泄露 Key。
- 编排：摘要成功时置顶，摘要失败或缺 Key 时仍调用 Server酱发送原始报告。
- 工作流：调度时间不变，两个 Secret 均从 GitHub Secrets 注入。
- 全量验收：Ruff lint、Ruff format、pytest、YAML 解析和 Secret 模式扫描通过。

## 风险控制

- DeepSeek 官方已宣布 `deepseek-chat` 将于 2026-07-24 停用，因此直接使用 `deepseek-v4-flash`。
- AI 不参与去重、行情计算或成功判定，避免模型故障影响基础报告。
- 新闻标题属于不可信输入，提示词明确只总结分隔区内容且不启用工具调用。
- 不记录 HTTP 响应正文和认证 Header。
- 不运行真实 Server酱或 DeepSeek 测试；集成测试使用注入的假响应，发布后由用户添加 Secret。
