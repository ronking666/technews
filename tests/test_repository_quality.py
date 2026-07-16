import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
REQUIRED_FILES = (
    ROOT / "LICENSE",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "CODE_OF_CONDUCT.md",
    ROOT / ".editorconfig",
    ROOT / ".gitattributes",
    ROOT / "pyproject.toml",
    ROOT / ".github" / "CODEOWNERS",
    ROOT / ".github" / "dependabot.yml",
    ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_professional_repository_files_exist():
    missing = [
        str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.is_file()
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


def test_repository_forces_lf_line_endings():
    attributes = read(ROOT / ".gitattributes")
    assert "* text=auto eol=lf" in attributes


def test_ci_runs_ruff_checks():
    ci = read(ROOT / ".github" / "workflows" / "ci.yml")
    assert "python -m ruff check ." in ci
    assert "python -m ruff format --check ." in ci


def test_dependabot_covers_supported_ecosystems():
    dependabot = read(ROOT / ".github" / "dependabot.yml")
    assert 'package-ecosystem: "pip"' in dependabot
    assert 'package-ecosystem: "github-actions"' in dependabot
