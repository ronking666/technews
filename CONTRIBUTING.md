# 贡献指南

感谢你愿意改进 TechNews。请保持变更小而清晰，并优先保证每日推送的稳定性。

## 开发环境

项目要求 Python 3.12 或更高版本。

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Windows PowerShell 激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

## 提交前检查

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

如需自动整理导入和格式：

```bash
python -m ruff check . --fix
python -m ruff format .
```

## 变更原则

- 不要在代码、日志、截图或测试数据中提交真实的 `SERVERCHAN_SENDKEY`。
- 修改定时时间时，同时更新工作流、README 和对应测试。
- 增加数据源时，必须保留单个来源失败时继续生成报告的行为。
- 增加外部依赖前，说明它的必要性、维护状态和失败影响。
- 涉及行情数据时，保留数据日期，避免把休市日数据描述为实时行情。

## Commit 约定

推荐使用 Conventional Commits 风格：

```text
feat: add configurable RSS source limits
fix: handle empty market history
docs: clarify ServerChan setup
test: cover partial source failures
chore: update development tools
```

## Pull Request 检查清单

- [ ] 变更目的和影响范围已经说明。
- [ ] Ruff 检查、格式检查和 pytest 均通过。
- [ ] 没有提交 Secret 或其他敏感信息。
- [ ] 调度、数据源或依赖变更已同步更新文档。
- [ ] 外部服务失败时仍有清晰且安全的错误行为。
