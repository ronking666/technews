# TechNews 每日早报

通过 GitHub Actions 自动获取科技资讯与财经行情，并使用 Server酱推送到微信。

## 推送时间

| 内容 | 北京时间 | GitHub Actions UTC |
| --- | --- | --- |
| 科技资讯 | 每天 05:30 | `30 21 * * *` |
| 财经与金属行情 | 每天 06:15 | `15 22 * * *` |

GitHub 的定时任务可能因平台负载延迟数分钟。两个任务相互独立，其中一个失败不会阻止另一个运行。

## 配置

1. 在 [Server酱](https://sct.ftqq.com/) 获取 SendKey。
2. 打开本仓库的 `Settings` → `Secrets and variables` → `Actions`。
3. 新建名为 `SERVERCHAN_SENDKEY` 的 Repository secret，并填入 SendKey。
4. 在仓库的 `Actions` 页面手动运行两个工作流，确认微信可以收到消息。

SendKey 只通过 GitHub Actions Secret 注入，不应写入代码、提交记录或日志。

## 失败规则

- 某个新闻源或行情标的失败：仍推送其他成功内容，并在报告中标注失败项。
- 所有上游数据均失败：尝试推送失败摘要，随后让工作流显示失败。
- Secret 缺失或 Server酱推送失败：工作流直接失败，并输出不含 SendKey 的错误信息。
- 财经报告会显示数据对应的实际交易日期，避免把休市日旧数据误认为实时行情。

## 本地运行

```bash
python -m venv .venv
python -m pip install -r requirements.txt
```

设置环境变量后运行：

```bash
python main.py
python finance.py
```

运行测试：

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## 数据来源说明

- 科技资讯来自公开 RSS。
- 行情通过 `yfinance` 获取。Yahoo Finance 数据及接口仅适合个人研究用途，不应将本项目输出视为投资建议。

