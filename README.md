# TechNews 每日早报

[![Tests](https://github.com/ronking666/technews/actions/workflows/ci.yml/badge.svg)](https://github.com/ronking666/technews/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

每天自动聚合科技资讯与财经行情，通过 GitHub Actions 定时生成 Markdown 报告，并使用 Server酱推送到微信。

## 功能亮点

- **完全自动化**：无需服务器，GitHub Actions 按北京时间每天执行。
- **两类独立报告**：科技资讯与财经行情互不影响，单个任务失败不会阻塞另一个。
- **容错获取**：单个 RSS 来源或行情标的失败时，仍推送其他有效内容。
- **安全推送**：SendKey 只通过 GitHub Actions Secret 注入，不写入代码或日志。
- **可验证**：pytest 覆盖数据处理、失败路径和工作流配置，Ruff 统一代码质量与格式。

## 推送时间

| 内容 | 北京时间 | GitHub Actions UTC |
| --- | --- | --- |
| 科技资讯 | 每天 05:30 | `30 21 * * *` |
| 财经与金属行情 | 每天 06:15 | `15 22 * * *` |

GitHub 的定时任务可能因平台负载延迟数分钟。两个任务使用独立工作流和并发组。

## 快速开始

### 1. 配置 Server酱

1. 在 [Server酱](https://sct.ftqq.com/) 获取 SendKey。
2. 打开仓库的 `Settings` → `Secrets and variables` → `Actions`。
3. 新建 Repository secret：名称填写 `SERVERCHAN_SENDKEY`，值填写 SendKey。
4. 打开 `Actions`，选择“每日科技资讯推送”或“每日财经行情推送”，使用 `Run workflow` 验证。

> [!IMPORTANT]
> 每手动运行一个推送工作流，会消耗一次 Server酱发送额度。测试前请先确认剩余额度。

仓库设为私有不会妨碍它运行自身的定时 Actions；只有有权限的账号才能查看代码、运行记录和日志。

### 2. 本地开发

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

如需在本地实际推送，请先临时设置 `SERVERCHAN_SENDKEY` 环境变量，再运行：

```bash
python main.py
python finance.py
```

这两个命令都会真实发送消息并消耗额度；普通开发验证应优先运行测试。

## 配置数据源

数据源统一保存在 [`technews/config.py`](technews/config.py)：

- `RSS_SOURCES`：科技资讯来源名称与 RSS 地址；
- `MARKET_TICKERS`：行情显示名称与 Yahoo Finance symbol；
- `REQUEST_TIMEOUT`：外部请求连接与读取超时；
- `APP_TIMEZONE`：报告日期使用的时区。

新增来源后，请同时增加测试，并确认单个来源失败时其他内容仍可推送。

## 项目结构

```text
.
├── .github/workflows/       # CI、科技早报与财经早报任务
├── technews/                # HTTP、RSS、行情、通知与配置模块
├── tests/                   # 单元测试和仓库质量测试
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
- 财经报告显示数据对应的实际交易日期，避免把休市日旧数据误认为实时行情。

## 质量保障

- **pytest**：覆盖时间转换、RSS 解析、行情计算、通知失败和工作流配置。
- **Ruff**：检查常见 Python 错误、导入顺序与统一格式。
- **GitHub Actions**：每次 push 和 Pull Request 都运行完整质量检查。
- **Dependabot**：每周检查 Python 依赖和 GitHub Actions 版本，更新仍需人工审核。

## 常见问题

### GitHub 显示“没有活动”是什么意思？

表示当前页面没有可显示的工作流运行记录，不代表代码一定有问题。确认仓库已启用 Actions、工作流位于默认分支，并可先手动运行一次验证。私有仓库的记录只有有权限的账号可见。

### 到点后没有立刻收到消息？

GitHub 的 cron 不是实时调度器，高峰期可能延迟数分钟。先查看对应 Actions 运行状态，再检查 `SERVERCHAN_SENDKEY`、Server酱额度和微信通知设置。

### 财经价格为什么不是当天日期？

周末、休市日或数据源延迟时，最新有效交易日可能早于报告日期。报告会明确显示实际数据日期。

### 一个数据源失败会导致整份报告消失吗？

不会。只要至少一个来源或标的成功，报告就会继续推送，并标记失败项。

## 安全与隐私

- 永远不要把 SendKey 提交到仓库、Issue、Pull Request、Actions 日志或截图。
- Secret 泄露后，应立即在 Server酱后台更换并更新 GitHub Repository secret。
- 安全问题请按照 [`SECURITY.md`](SECURITY.md) 私下报告。
- GitHub Actions 和第三方数据源会按各自的隐私政策处理网络请求。

## 数据来源与免责声明

- 科技资讯来自配置的公开 RSS，内容版权归原始发布者所有。
- 行情通过 `yfinance` 获取 Yahoo Finance 数据，仅适合个人研究。
- 本项目输出可能存在延迟、缺失或错误，不构成投资建议。

## 贡献

欢迎提交改进。开始前请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md) 和 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

## 许可证

本项目使用 [MIT License](LICENSE)。
