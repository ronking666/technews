# 用免费定时服务启动早报

新增的 20:30 纳指100期货晚报请另建第三个任务，具体填写见[晚报启用说明](evening-futures.md)；不要改动以下两份早报配置。

目标：每天北京时间 07:00 前收到科技和财经早报。cron-job.org 在 06:40 启动两个 GitHub 工作流，06:50 再启动一次作为补发检查；原有 GitHub 凌晨 schedule 保留作兜底（科技北京时间 04:27，财经纽约 16:47，即北京时间夏令时 04:47、冬令时 05:47），其实际执行仍可能延迟。

外部启动绕过 GitHub schedule 的触发延迟，程序仍在 GitHub 上运行。它不能保证 GitHub 执行资源、数据源、Server酱或微信始终准时。

## 方案选择举例

| 方法 | 用在本程序的例子 | 取舍 |
| --- | --- | --- |
| 已选择：免费外部定时服务 | cron-job.org 在 06:40/06:50 调用两个 GitHub 工作流 | 改动少，仍依赖 GitHub 执行资源；需要注册定时服务并配置触发令牌 |
| 云函数直接运行 | 腾讯云 SCF 定时运行新闻与行情程序 | 绕过 GitHub 调度和执行，需要云账号、部署及计费配置 |
| 自己的电脑定时 | Windows 任务计划在每天 06:40 启动程序 | 不需新增云服务，但电脑必须保持开机联网 |

云函数与电脑方案需要迁移运行环境和发送记录，不能简单与现有任务同时启用。官方说明：[腾讯云定时触发器](https://cloud.tencent.com/document/product/583/9708)、[Windows 任务计划](https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)。

## 1. 先上线仓库改动

先把本次修改合并到默认分支 `main`，确认 Tests 工作流通过，再启用外部定时服务。新工作流带有“检查当天发送记录”和“保存发送记录”步骤，缺少这些步骤时重复启动可能重复发微信。

上线当天旧版程序已经发送过的消息没有新回执。建议让外部任务从次日早上开始生效；当天第一次手动运行新版程序可能多发一份。不要为了测试连续运行旧版工作流。

两份日报各自保存一个当天成功回执，保留 7 天。相同报告再次启动时，检查到该回执就跳过抓取、AI 和推送。同一报告的手动、外部、原生定时任务使用相同并发组，避免同时发送。

## 2. 创建仅用于启动任务的 GitHub 令牌

打开 [GitHub fine-grained personal access token 设置](https://github.com/settings/personal-access-tokens/new)：

1. Token name 填 `technews-external-scheduler`。
2. Resource owner 选 `ronking666`。
3. Repository access 选 **Only select repositories**，只选 `technews`。
4. Repository permissions 只增加 **Actions: Read and write**；Metadata 的只读权限由 GitHub 自动添加。不需要 Contents 写权限。
5. 设置合适的有效期，记下到期日，到期前更新定时服务中的令牌。
6. 生成后只粘贴到 cron-job.org 的请求头设置中。不要贴到聊天、仓库文件、Issue 或截图中。

这个令牌让定时服务启动仓库任务。Server酱和 DeepSeek 的密钥继续保留在 GitHub Secrets，外部定时服务不需要它们。

## 3. 在 cron-job.org 创建两个任务

在 [cron-job.org](https://cron-job.org/en/) 注册并登录后，创建下面两个任务。先关闭任务的启用开关，检查配置后再启用。

| 设置 | 科技早报 | 财经早报 |
| --- | --- | --- |
| Title | TechNews 科技早报 | TechNews 财经早报 |
| URL | `https://api.github.com/repos/ronking666/technews/actions/workflows/daily_news.yml/dispatches` | `https://api.github.com/repos/ronking666/technews/actions/workflows/daily_finance.yml/dispatches` |
| 时区 | `Asia/Shanghai` | `Asia/Shanghai` |
| 自定义时间 | 每天 06:40 和 06:50 | 每天 06:40 和 06:50 |
| HTTP method | `POST` | `POST` |
| Request body | `{"ref":"main"}` | `{"ref":"main"}` |

如果自定义时间界面按字段选择：小时只选 **6**，分钟只选 **40、50**，日期、月份、星期都选“每天/全部”。保存后检查 Next executions 确实是北京时间 06:40、06:50，而不是每小时运行。

在 Advanced / Headers 中，为两个任务分别填写：

| 请求头 | 值 |
| --- | --- |
| `Authorization` | `Bearer ` 后紧接刚生成的 GitHub 令牌 |
| `Accept` | `application/vnd.github+json` |
| `Content-Type` | `application/json` |
| `X-GitHub-Api-Version` | `2026-03-10` |
| `User-Agent` | `technews-external-scheduler` |

请求超时可设 30 秒。这次请求只负责启动，不等待日报生成。开启失败、恢复及自动停用通知；关闭保存响应也不影响工作流执行。

[cron-job-examples.json](cron-job-examples.json) 给出了已填好仓库地址和时间的两个 API 配置示例。文件中的令牌只是占位符，每个 `job` 要分别创建；它不是控制台的一键导入文件。使用控制台填写即可，不必申请 cron-job.org API key。

## 4. 怎么确认已经生效

1. 在 cron-job.org 检查“下次运行时间”与时区。
2. 次日 06:40 后打开 [GitHub Actions](https://github.com/ronking666/technews/actions)。应出现由 `workflow_dispatch` 启动的两项任务。
3. 如果 06:40 的任务实际发送了日报，看“运行科技资讯推送”/“运行财经行情推送”的成功日志，确认“保存发送记录”成功，运行页面出现 `technews-sent-news-日期` 或 `technews-sent-finance-日期` artifact。如果原有凌晨任务已经先发过，06:40 显示“当天已发送，跳过”也是正常成功；应去当天较早的原生任务运行页面核对回执及微信消息。
4. 06:50 的第二次启动应显示“当天已发送，跳过”，发送步骤不执行。
5. 微信收到两份日报后，核对消息时间。至少观察连续几天，才能判断准点率是否改善。

GitHub API 返回 200（本例 API 版本）只表示启动请求已接受，不代表微信已经收到。定时服务显示“成功”也只说明启动接口成功；报告是否发出仍以 GitHub 发送步骤和微信消息为准。

如果确实需要手动验证，在默认分支运行一个工作流即可；首次运行可能实际发送微信并消耗额度。第二次运行在回执存在时应跳过。不要删除当天回执后反复测试。

## 5. 常见失败与恢复

- **401/403/404**：检查令牌是否过期、是否只选了正确仓库、是否有 Actions 写权限、URL 与 `ref` 是否正确。私有仓库权限不足也可能显示 404。
- **触发成功但 GitHub 没有开始执行**：检查是否有等待中的运行、Actions 是否启用以及 GitHub 平台状态。外部触发无法解决 GitHub 执行资源拥堵。
- **检查发送记录失败**：本次停止，不把未知状态当作没发送；检查 GitHub token 的 Actions 读权限和 GitHub API 状态。06:50 会再次尝试。
- **临近北京时间零点**：23:45 起停止新发送，避免最长 10 分钟的任务跨日后把回执记在前一天；请次日重试。此限制不影响清晨定时任务。
- **发送失败**：不保存成功回执，06:50 可再次尝试。所有上游数据均失败时，原程序可能先发一份失败摘要再退出失败；补发仍会尝试获取数据。
- **发送成功但保存记录失败**：消息可能已经发出，下一次启动可能重复。先检查微信与发送日志，必要时暂停当天外部任务，修复 artifact 存储或上传问题后再恢复。
- **HTTP 超时**：对方可能已经接受请求或消息，不能据此断定没发送。并发组与回执可减少重复，但不能提供端到端“绝不重复”的保证。

若成功发送后流程被取消、回执上传失败，或人为删除回执，后续运行仍可能再次发送。本项目的每日回执是正常运行中的重复抑制，不是 Server酱端到端幂等机制。

## 6. 暂停或回退

在 cron-job.org 关闭这两个任务即可停止外部触发；GitHub 原有凌晨定时任务仍可兜底，但可能延迟。需要完全停发时，再到 GitHub Actions 停用两个日报工作流。

后续若迁移到云函数直接运行，应重新设计共享发送记录；不能让云函数和 GitHub 各自独立判断后同时发送。

## 官方资料

- [cron-job.org 功能和免费说明](https://cron-job.org/en/)
- [cron-job.org 请求、时间和通知参数](https://docs.cron-job.org/rest-api.html)
- [GitHub 启动工作流接口与所需权限](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
- [GitHub artifact 查询接口](https://docs.github.com/en/rest/actions/artifacts#list-artifacts-for-a-repository)
