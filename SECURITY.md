# 安全策略

## 支持范围

安全修复只针对 `main` 分支的最新版本。

## 私下报告漏洞

请不要为安全问题创建公开 Issue。优先使用仓库的
[GitHub Security Advisories](https://github.com/ronking666/technews/security/advisories/new)
提交私密报告，并提供：

- 受影响的文件或工作流；
- 可复现步骤与实际影响；
- 已做脱敏处理的日志；
- 建议的修复方向（如有）。

## Secret 安全

- `SERVERCHAN_SENDKEY` 只能保存在 GitHub Actions Repository Secret 中。
- 不要把 SendKey 粘贴到 Issue、Pull Request、Actions 日志或截图。
- 如果 SendKey 意外泄露，应立即在 Server酱后台更换，并更新 GitHub Secret。
- 安全报告中请使用 `***` 替换任何凭据、令牌或个人信息。
