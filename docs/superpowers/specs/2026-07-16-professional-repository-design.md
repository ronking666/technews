# TechNews 仓库专业化设计

## 目标

在不改变科技资讯、财经行情、Server酱调用方式和每日调度时间的前提下，让仓库达到易理解、易维护、易协作、可持续更新的个人 Python 项目标准。

## 方案选择

采用“平衡专业化”方案：同时改善仓库门面、协作规范和自动化质量保障。相比只修改 README，它能持续防止质量回退；相比改造成可安装 CLI 和正式发布包，它不引入当前项目不需要的复杂度。

## 范围

### 仓库门面

- 重写 `README.md`，补充状态徽章、功能亮点、快速开始、推送时间、配置入口、目录结构、质量保障、常见问题、安全说明和许可证。
- 增加 MIT `LICENSE`，版权主体使用仓库账号 `ronking666`，避免猜测个人法定姓名。
- 增加 `CONTRIBUTING.md`、`SECURITY.md` 和简洁的 `CODE_OF_CONDUCT.md`。
- 增加 Bug、功能建议 Issue 表单和 Pull Request 模板。
- 增加 `.editorconfig` 统一基础文本格式。

### 工程质量

- 增加 `pyproject.toml`，集中保存 pytest 与 Ruff 配置，但不把项目改造成可安装包。
- 在 `requirements-dev.txt` 固定兼容 Python 3.12 的 Ruff 版本。
- CI 依次执行 Ruff 代码检查、Ruff 格式检查和完整 pytest 测试。
- 增加仓库质量测试，验证关键专业化文件、CI 命令和 Dependabot 配置持续存在。
- 增加 Dependabot，每周检查 Python 依赖与 GitHub Actions 版本。

### GitHub 元数据

- 仓库描述设置为“每天通过 GitHub Actions 获取科技资讯与财经行情，并使用 Server酱推送到微信”。
- Topics 设置为 `python`、`github-actions`、`serverchan`、`rss`、`daily-report`、`yfinance`、`wechat`。

## 非目标

- 不修改 `main.py`、`finance.py` 或 `technews/` 的运行时行为。
- 不修改北京时间 05:30 与 06:15 的正式调度。
- 不触发 Server酱测试消息，不消耗发送额度。
- 不启用分支保护或其他可能阻碍个人直接维护的仓库规则。
- 本轮不实现产品新功能；只在交付说明中给出后续路线图。

## 数据流与错误处理

现有数据流保持不变：GitHub Actions 定时触发脚本，脚本获取 RSS 或 Yahoo Finance 数据，渲染 Markdown，再通过 Secret 注入的 SendKey 调用 Server酱。现有的部分成功继续推送、全部失败发送摘要、推送失败令工作流失败等规则全部保留。

专业化改造只在提交和拉取请求阶段增加静态检查。Ruff 或 pytest 失败时 CI 阻止有问题的变更通过；Dependabot 仅创建依赖更新建议，不自动合并。

## 测试与验收

- 先编写会因专业化文件缺失而失败的仓库质量测试。
- 增加文件与配置后，运行 `python -m ruff check .`。
- 运行 `python -m ruff format --check .`。
- 运行 `python -m pytest -q`，现有 33 个测试与新增质量测试必须全部通过。
- 推送后确认 GitHub Actions 的 `Tests` 工作流成功。
- 确认远程 `main` 与本地交付提交一致，工作区无未提交文件。

## 风险控制

- 文档不展示真实 SendKey，也不建议把密钥写入文件。
- 依赖与 Actions 更新由 Dependabot 提醒，仍由维护者审核。
- 不加入会因为外部漏洞数据库波动而突然阻塞 CI 的强制审计任务。
- 不引入打包、发布和预提交钩子，避免给小型个人项目增加维护负担。
