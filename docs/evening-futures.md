# 新增每天 20:30 的纳指100期货微信晚报

已有两份早报继续运行。新增工作流 `daily_futures.yml`，复用 GitHub Secrets 中的 `SERVERCHAN_SENDKEY`；不需要新增行情密钥，也不调用 AI。

## 晚报包含什么

| 标的 | Yahoo 代码 | 价格单位 |
| --- | --- | --- |
| E-mini 纳指100期货（主标的） | NQ=F | 点 |
| 标普500期货 | ES=F | 点 |
| 道指期货 | YM=F | 点 |
| 美元指数 | DX-Y.NYB | 点 |
| 黄金期货 | GC=F | 美元/盎司 |
| WTI原油期货 | CL=F | 美元/桶 |

每项显示最新可得价格、数据源名称、北京时间报价时间、参考前收与涨跌、可用的日内高低和成交量。Yahoo 报价可能延迟；NQ=F 是滚动报价，数据源显示的合约名称会随换月改变，不是永久固定的合约。

参考前收采用数据源 `previousClose`，缺失时使用同一次 1 日查询的 `chartPreviousClose`，不将其标为交易所结算价。缺失数据写“暂缺”，不填零。超过 120 分钟提示“报价较旧，可能休市或数据延迟”；周末也会发送带原始时间的最后可得报价。

## 在 cron-job.org 增加第三个任务

代码合并到 `main` 后，在你已登录的 [cron-job.org 控制台](https://console.cron-job.org/jobs)点击“创建计划任务”，填写：

| 页面 | 项目 | 填写内容 |
| --- | --- | --- |
| 常规 | 标题 | 纳指100期货晚报 |
| 常规 | 网址 | `https://api.github.com/repos/ronking666/technews/actions/workflows/daily_futures.yml/dispatches` |
| 常规 | 运行计划 | 自订，小时仅选 **20**，分钟选 **30 和 40**，日期/月份/星期全部 |
| 常规 | Crontab 预览 | `30,40 20 * * *` |
| 进阶 | 时区 | `Asia/Shanghai` |
| 进阶 | 请求方法 | `POST` |
| 进阶 | 请求本体 | `{"ref":"main"}` |
| 进阶 | 请求超时 | 30 秒 |

“进阶 → 标头”沿用现有财经早报任务的请求头：

| 键 | 值 |
| --- | --- |
| Authorization | `Bearer ` 后接现有 GitHub 触发令牌 |
| Accept | `application/vnd.github+json` |
| Content-Type | `application/json` |
| X-GitHub-Api-Version | `2026-03-10` |
| User-Agent | `technews-external-scheduler` |

键名直接输入，不加反引号或引号。令牌只填在服务网页，别发到聊天或截图。只要现有令牌仍有效、仓库为 `technews` 且 Actions 为 Read and write，就可复用，无需再申请。该令牌已知到期日为 2027-02-02；若后来换过令牌，以 GitHub 当前显示为准。

设置完打开“激活任务”，点击“创建”保存。任务列表应新增绿色状态的晚报，下一次时间是北京时间 20:30；自订计划预览随后为 20:40。不要修改两份早报的时间。

可先点一次“测试运行”：接口成功表示已启动 GitHub，随后在[晚报 Actions 页面](https://github.com/ronking666/technews/actions/workflows/daily_futures.yml)确认发送步骤与回执，并核对微信。当天已有晚报回执时会跳过，不会为测试强制重复发送。

## 发送和补发

- 每天 20:30 启动，20:40 再检查；微信收到时间要加上 GitHub 排队、抓取和推送耗时。
- GitHub 原生定时同为北京时间 20:30，外部服务与原生触发共用并发组和 `technews-sent-futures-日期` 回执；已成功发送时自动跳过。
- 相关行情部分失败仍发可用数据；NQ 缺失或全部失败时，会发提示并返回失败，不保存成功回执，允许下一次补查重试，因此可能收到两份失败提示。
- 单个标的最多请求两次、每次超时 15 秒。请求失败不会回退到现货指数，也不会编造期货报价。
- 原生 GitHub 定时仍可能延迟；外部任务必须在 cron-job.org 保存并启用，仓库文件不会代替这一步。

## 预览与暂停

`python futures.py --preview` 只预览真实数据，不发微信。新增的 `Futures live data check` 在涉及行情代码的 PR 上执行此命令，不读取推送密钥；它和单元测试分开，便于发现运行环境访问数据源的问题。

暂停晚报：先在 cron-job.org 停用第三个任务，再在 GitHub Actions 停用“每日纳指100期货晚报”。两份早报无需停用。

数据与接口资料：[CME 纳指100期货](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html)、[Yahoo NQ 行情](https://finance.yahoo.com/chart/NQ%3DF)、[GitHub workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)。
