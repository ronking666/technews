# TechNews Professional Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变正式推送行为与时间的前提下，补齐 TechNews 的仓库门面、协作规范、静态质量检查、依赖维护和 GitHub 元数据。

**Architecture:** 保持现有运行时模块和三个工作流的数据流不变，在仓库外围增加文档与社区健康文件；用 `pyproject.toml` 集中配置 pytest/Ruff，用现有 CI 执行 lint、format-check 与 tests；用仓库质量测试锁定关键配置。

**Tech Stack:** Python 3.12、pytest 9.1.1、Ruff 0.15.20、GitHub Actions、Dependabot、GitHub Issue Forms

## Global Constraints

- `main.py`、`finance.py`、`technews/` 的运行时行为不得改变。
- 新闻与财经工作流继续使用北京时间 05:30 和 06:15。
- 不运行任何正式推送脚本，不消耗 Server酱额度。
- 不把 `SERVERCHAN_SENDKEY` 或 GitHub 凭据写入文件、提交或日志。
- 不启用分支保护，不增加打包、发布或预提交钩子。

---

### Task 1: 用测试锁定专业仓库基线

**Files:**
- Create: `tests/test_repository_quality.py`

**Interfaces:**
- Consumes: 仓库根目录、`.github/workflows/ci.yml` 与后续任务创建的静态文件。
- Produces: 关键文件、README、Python 工具和依赖维护的自动化验收。

- [ ] **Step 1: 写入失败测试**

```python
import tomllib
from pathlib import Path


ROOT = Path(__file__).parents[1]
REQUIRED_FILES = (
    ROOT / "LICENSE",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "CODE_OF_CONDUCT.md",
    ROOT / ".editorconfig",
    ROOT / "pyproject.toml",
    ROOT / ".github" / "dependabot.yml",
    ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_professional_repository_files_exist():
    missing = [
        str(path.relative_to(ROOT))
        for path in REQUIRED_FILES
        if not path.is_file()
    ]
    assert missing == []


def test_readme_has_key_maintenance_sections():
    readme = read(ROOT / "README.md")
    for heading in (
        "## 功能亮点",
        "## 快速开始",
        "## 项目结构",
        "## 质量保障",
        "## 常见问题",
        "## 安全与隐私",
    ):
        assert heading in readme


def test_python_tooling_is_configured():
    config = tomllib.loads(read(ROOT / "pyproject.toml"))
    assert config["tool"]["ruff"]["target-version"] == "py312"
    assert config["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]


def test_ci_and_dependabot_cover_quality_and_dependencies():
    ci = read(ROOT / ".github" / "workflows" / "ci.yml")
    assert "python -m ruff check ." in ci
    assert "python -m ruff format --check ." in ci
    dependabot = read(ROOT / ".github" / "dependabot.yml")
    assert 'package-ecosystem: "pip"' in dependabot
    assert 'package-ecosystem: "github-actions"' in dependabot
```

- [ ] **Step 2: 运行测试并确认它因缺失专业化文件而失败**

Run: `python -m pytest tests/test_repository_quality.py -q`

Expected: FAIL，报告 `LICENSE`、`pyproject.toml` 或 `.github/dependabot.yml` 缺失。

---

### Task 2: 增加 Python 质量工具与依赖维护

**Files:**
- Create: `pyproject.toml`
- Create: `.editorconfig`
- Create: `.github/dependabot.yml`
- Modify: `requirements-dev.txt`
- Modify: `.github/workflows/ci.yml`
- Modify: Python files only when Ruff applies deterministic import sorting or formatting

**Interfaces:**
- Consumes: Task 1 的配置断言和现有依赖文件。
- Produces: `python -m ruff check .`、`python -m ruff format --check .`、`python -m pytest -q`。

- [ ] **Step 1: 写入 `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "B", "UP"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"
```

- [ ] **Step 2: 写入 `.editorconfig`、Dependabot，并把 `ruff==0.15.20` 加到 `requirements-dev.txt`**

Dependabot 必须各有一个 `pip` 与 `github-actions` 更新项；二者均在 `Asia/Shanghai` 时区每周一 09:00 检查，最多打开 5 个 PR。

- [ ] **Step 3: 在 CI 的 pytest 前增加以下两个步骤**

```yaml
      - name: 检查代码质量
        run: python -m ruff check .

      - name: 检查代码格式
        run: python -m ruff format --check .
```

- [ ] **Step 4: 安装并执行确定性修复**

Run: `python -m pip install -r requirements-dev.txt`

Expected: pytest 9.1.1 与 Ruff 0.15.20 安装成功。

Run: `python -m ruff check . --fix`

Expected: 只执行导入排序等安全修复，退出码为 0。

Run: `python -m ruff format .`

Expected: Python 文件格式化完成，业务断言和字符串内容不变。

---

### Task 3: 补齐文档与协作入口

**Files:**
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `.github/CODEOWNERS`
- Create: `.github/PULL_REQUEST_TEMPLATE.md`
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: 现有调度、配置、失败规则和 Task 2 的质量命令。
- Produces: 快速开始入口、贡献与安全报告入口、结构化 Issue/PR 信息。

- [ ] **Step 1: 增加维护规范**

`LICENSE` 使用标准 MIT 文本，版权行为 `Copyright (c) 2026 ronking666`。`CONTRIBUTING.md` 包含环境准备、三条质量命令、变更原则、Conventional Commits 示例和 PR 检查清单。`SECURITY.md` 指向 GitHub Security Advisories，禁止公开 SendKey。`CODE_OF_CONDUCT.md` 覆盖尊重沟通、禁止骚扰与泄密、维护者执行权限。`.github/CODEOWNERS` 内容为 `* @ronking666`。

- [ ] **Step 2: 增加协作模板**

PR 模板收集变更、验证、风险、调度和 Secret 影响。Bug 表单收集复现、预期、Actions 摘要、环境和脱敏确认。功能表单收集场景、方案、替代方案和外部服务/推送次数影响。Issue 配置关闭空白 Issue，并把安全问题链接到 `https://github.com/ronking666/technews/security/advisories/new`。

- [ ] **Step 3: 重写 README**

章节顺序固定为：标题与徽章、定位说明、功能亮点、推送时间、快速开始、配置数据源、项目结构、失败规则、质量保障、常见问题、安全与隐私、数据来源与免责声明、贡献、许可证。快速开始明确每次手动工作流消耗一次发送额度，以及私有仓库不影响仓库自身的定时 Actions。

- [ ] **Step 4: 运行仓库质量测试**

Run: `python -m pytest tests/test_repository_quality.py -q`

Expected: PASS。

---

### Task 4: 全量验证、发布与 GitHub 元数据

**Files:**
- Modify: 仅 Ruff 自动格式化确认需要修改的 Python 文件
- External: GitHub repository description and topics

**Interfaces:**
- Consumes: Tasks 1-3 的全部输出。
- Produces: 远程 `main` 的专业化仓库与成功的 GitHub Actions 运行。

- [ ] **Step 1: 执行完整本地验收**

Run: `python -m ruff check .`

Expected: `All checks passed!`。

Run: `python -m ruff format --check .`

Expected: 所有 Python 文件已格式化。

Run: `python -m pytest -q`

Expected: 原有 33 个测试加新增质量测试全部通过。

Run: `git diff --check`

Expected: 无输出。

- [ ] **Step 2: 检查范围并提交**

Run: `git status --short` 与 `git diff --stat`，确认只有设计范围内文件后提交 `chore: professionalize repository`。

- [ ] **Step 3: 发布到 main**

Run: `git push origin HEAD:main`

Expected: 远程 `main` 快进到专业化提交，不触发任何 Server酱推送工作流。

- [ ] **Step 4: 更新 GitHub 元数据**

通过已认证的 GitHub API，把描述设为“每天通过 GitHub Actions 获取科技资讯与财经行情，并使用 Server酱推送到微信”，Topics 设为 `python`、`github-actions`、`serverchan`、`rss`、`daily-report`、`yfinance`、`wechat`，调用过程不得输出认证令牌。

- [ ] **Step 5: 验证远程状态**

确认 `Tests` 工作流结论为 `success`，远程 `main` SHA 等于本地 HEAD，工作区干净。
