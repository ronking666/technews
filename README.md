# TechNews 每日早报

[![Tests](https://github.com/ronking666/technews/actions/workflows/ci.yml/badge.svg)](https://github.com/ronking666/technews/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

每天自动聚合科技资讯与财经行情，通过 GitHub Actions 定时生成 Markdown 报告，并使用 Server酱推送到微信。

## 功能亮点

- **完全自动化**：无需服务器，GitHub Actions 按北京时间每天执行。
- **两类独立报告**：科技资讯与财经行情互不影响，单个任务失败不会阻塞另一个。
- **更清晰的新闻**：自动合并跨来源重复标题，并用 `🔥` 标出关注关键词。
- **中文全球科技覆盖**：通过国内可直接访问的中文科技媒体，汇总全球 AI、软件、科学、安全、创业和科技产业动态。
- **增强的财经趋势**：同时展示 5 日、20 日涨跌和近 20 个交易日价格区间。
- **可选 AI 摘要**：使用 DeepSeek V4 Flash 生成中文要点，失败时自动回退到完整原报告。
- **容错获取**：单个 RSS 来源或行情标的失败时，仍推送其他有效内容。
- **安全推送**：SendKey 和 DeepSeek API Key 只通过 GitHub Actions Secret 注入，不写入代码或日志。
- **可验证**：pytest 覆盖数据处理、失败路径和工作流配置，Ruff 统一代码质量与格式。

## 推送时间

| 内容 | 预计北京时间 | 调度基准 |
| --- | --- | --- |
| 科技资讯 | 每天 04:27 | `Asia/Shanghai` 04:27 |
| 财经与金属行情 | 夏令时约 04:47、冬令时约 05:47 | `America/New_York` 16:47 |

科技任务整体前移，用于吸收 GitHub Actions 的排队延迟。财经任务绑定纽约时间，始终在美股 16:00 收盘后 47 分钟运行，既提早发送，又避免固定北京时间在冬季跑到收盘前。两个任务使用独立工作流和并发组。

GitHub 的定时任务不是实时调度器，高负载时仍可能延迟；这里的时间是目标启动时间，不是送达承诺。

## 快速开始

### 1. 配置 Server酱

1. 在 [Server酱](https://sct.ftqq.com/) 获取 SendKey。
2. 打开仓库的 `Settings` → `Secrets and variables` → `Actions`。
3. 新建 Repository secret：名称填写 `SERVERCHAN_SENDKEY`，值填写 SendKey。
4. 打开 `Actions`，选择“每日科技资讯推送”或“每日财经行情推送”，使用 `Run workflow` 验证。

> [!IMPORTANT]
> 每手动运行一个推送工作流，会消耗一次 Server酱发送额度。测试前请先确认剩余额度。

仓库设为私有不会妨碍它运行自身的定时 Actions；只有有权限的账号才能查看代码、运行记录和日志。

### 2. 配置 DeepSeek 摘要（可选）

1. 在 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys) 创建 API Key。
2. 打开仓库的 `Settings` → `Secrets and variables` → `Actions`。
3. 新建 Repository secret：名称填写 `DEEPSEEK_API_KEY`，值填写 API Key。

不要把 API Key 粘贴到聊天、代码、Issue 或日志中。未配置密钥、额度不足或接口暂时不可用时，早报仍会发送，只是不包含 AI 摘要。

项目默认使用 `deepseek-v4-flash` 非思考模式；模型、超时和摘要长度可在 `config.toml` 中调整。

### 3. 本地开发

项目要求 Python 3.12 或更高版本：

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

运行质量检查：

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

如需在本地实际推送，请先临时设置 `SERVERCHAN_SENDKEY`；需要 AI 摘要时再设置 `DEEPSEEK_API_KEY`，然后运行：

```bash
python main.py
python finance.py
```

这两个命令都会真实发送消息并消耗额度；普通开发验证应优先运行测试。

## 配置数据源

可修改项统一保存在 [`config.toml`](config.toml)：

- `[news]`：RSS 来源、每源条数、去重开关和高亮关键词；
- `[finance]`：行情标的、历史周期、趋势窗口和价格区间天数；
- `[ai]`：DeepSeek 开关、V4 模型、超时和输入输出上限。

`technews/config.py` 只保留程序运行常量和兼容入口。配置在程序启动时严格校验，拼写错误或不安全的地址会直接给出明确错误。

新增来源后，请同时增加测试，并确认单个来源失败时其他内容仍可推送。

默认新闻来源包含 IT之家、少数派、爱范儿，以及雷峰网、极客公园、InfoQ中文、Solidot、36氪和钛媒体。

## 项目结构

```text
.
├── .github/workflows/       # CI、科技早报与财经早报任务
├── technews/                # HTTP、RSS、行情、AI 摘要、通知与配置模块
├── tests/                   # 单元测试和仓库质量测试
├── config.toml              # 新闻、财经和 AI 的可编辑配置
├── main.py                  # 科技资讯报告入口
├── finance.py               # 财经行情报告入口
├── requirements.txt         # 运行时依赖
├── requirements-dev.txt     # 测试与代码质量依赖
└── pyproject.toml           # pytest 与 Ruff 配置
```

## 失败规则

- 某个新闻源或行情标的失败：仍推送其他成功内容，并在报告中标注失败项。
- 所有上游数据均失败：尝试推送失败摘要，随后让工作流显示失败。
- Secret 缺失或 Server酱推送失败：工作流直接失败，并输出不含 SendKey 的错误信息。
- DeepSeek 密钥缺失或摘要调用失败：跳过 AI 摘要，继续发送确定性的原始报告。
- 财经报告显示数据对应的实际交易日期，避免把休市日旧数据误认为实时行情。
- 纳指会用 FRED 官方日线补齐 Yahoo Finance 的历史缺口；若官方历史暂时不可用，则将纳指标记为获取失败，不用可能错误的涨跌幅继续生成摘要。

## 质量保障

- **pytest**：覆盖时间转换、RSS 解析、行情计算、通知失败和工作流配置。
- **Ruff**：检查常见 Python 错误、导入顺序与统一格式。
- **GitHub Actions**：每次 push 和 Pull Request 都运行完整质量检查。
- **Dependabot**：每周检查 Python 依赖和 GitHub Actions 版本，更新仍需人工审核。

## 常见问题

### GitHub 显示“没有活动”是什么意思？

表示当前页面没有可显示的工作流运行记录，不代表代码一定有问题。确认仓库已启用 Actions、工作流位于默认分支，并可先手动运行一次验证。私有仓库的记录只有有权限的账号可见。

### 到点后没有立刻收到消息？

GitHub 的 `schedule` 在平台高负载时可能延迟，任务只有在 Actions 页面出现运行记录后才真正开始。项目已将科技任务提前到北京时间 04:27，并把财经任务绑定到纽约收盘后 16:47，以吸收常见排队时间且保护行情完整性。若仍未收到，先查看对应 Actions 的“创建时间”和完成状态，再检查 `SERVERCHAN_SENDKEY`、Server酱额度和微信通知设置。

### 财经价格为什么不是当天日期？

周末、休市日或数据源延迟时，最新有效交易日可能早于报告日期。报告会明确显示实际数据日期。

### 纳指为什么偶尔显示获取失败？

纳指最新价格来自 Yahoo Finance，历史交易日同时用 FRED 的 `NASDAQ100` 官方序列校验和补齐。若任一来源暂时无法提供足够数据，程序会优先停止该标的计算，避免把隔了多个交易日的价格误算成“当日涨跌”。

### 一个数据源失败会导致整份报告消失吗？

不会。只要至少一个来源或标的成功，报告就会继续推送，并标记失败项。

### 为什么报告里没有 AI 摘要？

先确认仓库 Actions Secret 中存在 `DEEPSEEK_API_KEY`，再检查 DeepSeek 账户额度。即使 AI 不可用，项目也会保留原始新闻和行情推送，避免影响每天收报。

## 安全与隐私

- 永远不要把 SendKey 或 DeepSeek API Key 提交到仓库、聊天、Issue、Pull Request、Actions 日志或截图。
- Secret 泄露后，应立即在对应服务后台撤销并更新 GitHub Repository secret。
- 安全问题请按照 [`SECURITY.md`](SECURITY.md) 私下报告。
- GitHub Actions 和第三方数据源会按各自的隐私政策处理网络请求。

## 数据来源与免责声明

- 科技资讯来自配置的公开 RSS，内容版权归原始发布者所有。
- 行情主要通过 `yfinance` 获取 Yahoo Finance 数据；纳指历史交易日另用 FRED 的 `NASDAQ100` 序列补齐与校验，仅适合个人研究。
- AI 摘要会把截断后的报告内容发送给 DeepSeek；摘要可能遗漏或误解信息，请以原文和实际数据为准。
- 本项目输出可能存在延迟、缺失或错误，不构成投资建议。

## 贡献

欢迎提交改进。开始前请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md) 和 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

## 许可证

本项目使用 [MIT License](LICENSE)。
