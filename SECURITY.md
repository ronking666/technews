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

- `SERVERCHAN_SENDKEY` 和 `DEEPSEEK_API_KEY` 只能保存在 GitHub Actions Repository Secret 中。
- 不要把 SendKey 或 API Key 粘贴到聊天、Issue、Pull Request、Actions 日志或截图。
- 如果凭据意外泄露，应立即在对应服务后台撤销，并更新 GitHub Secret。
- 安全报告中请使用 `***` 替换任何凭据、令牌或个人信息。
