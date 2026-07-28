# NDX 数据完整性修复设计

## 目标

修复 Yahoo Finance 的 `^NDX` 日线缺失收盘价时，程序把非相邻交易日误算为“当日涨跌”的问题。在保留早报时效的同时，用 Nasdaq/FRED 官方日线补齐历史缺口；无法确认数据完整性时不输出可能错误的纳指指标。

## 已确认根因

2026-07-28 财经早报中，Yahoo 原始 chart 接口返回：

- 2026-07-23：`Close = 28454.81`
- 2026-07-24：`Close = null`
- 2026-07-27：`Close = 28039.21`

`yfinance` 删除了 7月24日空值行。现有 `market_result_from_history` 又执行 `dropna()` 并直接取最后两行，因此把 7月23日当成前一交易日，得到错误的 `-415.60（-1.46%）`。Nasdaq/FRED 的完整数据表明 7月24日收盘为 `28128.34`，正确结果是 `-89.13（-0.32%）`。相同缺口还移动了 5日和20日趋势的基准行。

## 方案选择

### 仅使用 Yahoo quote 元数据

拒绝。当前 `previousClose` 为空，`chartPreviousClose` 受请求区间影响，而且无法修补 5日、20日历史窗口。

### 全部改用 FRED

拒绝。FRED 的 Nasdaq 日线权威但通常在美股收盘数小时后更新，早报运行时可能还没有当天收盘值，会降低时效。

### Yahoo 当前值 + FRED 历史补齐（采用）

Yahoo 继续提供及时的当天收盘；FRED `NASDAQ100` 系列提供完整的官方历史收盘。计算前以交易日期为键合并两者：Yahoo 的有效值优先，FRED 只填补缺失日期。这样既保留当天时效，又能修复历史断层。

## 模块边界

### `technews/fred.py`

新增独立数据提供模块：

```python
fetch_fred_closes(
    series_id: str,
    start: date,
    end: date,
    *,
    get: Callable[..., Any] = requests.get,
) -> dict[date, float]
```

它调用 FRED CSV 图表接口，校验 HTTP 状态、CSV 列名、日期、有限数值和非空结果。`.`、空白和非有限值不进入结果；网络错误、无效 CSV 或无有效数据统一抛出 `MarketDataError`，不暴露响应正文。

### `technews/market.py`

新增 FRED symbol 映射：

```python
OFFICIAL_HISTORY_SERIES = {"^NDX": "NASDAQ100"}
```

`market_result_from_history` 增加可选 `fallback_closes`。内部不再只依赖 DataFrame 行位置，而是把 Yahoo 与备用收盘价统一成按 `date` 排序的有效观测：

1. 读取 Yahoo `Close` 的有限值。
2. 使用 `setdefault` 加入 FRED 值，因此不会覆盖及时的 Yahoo 当天值。
3. 按日期排序后计算前收、趋势窗口与区间。

`fetch_market_result` 对 `^NDX` 获取 Yahoo 历史后，再按同一日期范围请求 FRED，并把结果传给计算函数。其他标的仍只使用 Yahoo，不增加额外请求。

## 失败策略

- Yahoo 当前值有效、FRED 成功：合并后计算并发送。
- Yahoo 当前值无效：保持现有重试和“获取失败”。
- `^NDX` 的 FRED 请求或解析失败：本次纳指显示“获取失败”，不回退到未经校验的 Yahoo 结果。
- 单个纳指标的失败不阻塞黄金、白银、铜、铂金和 REMX。
- FRED 模块不记录响应正文、请求异常详情或任何 Secret。

这是偏向正确性的 fail-closed 选择：宁可暂时少一项纳指，也不发送错误涨跌幅。FRED 无需 API Key，不增加 Secret。

## 重试与性能

沿用 `fetch_market_result` 的最多三次尝试。每次尝试包含 Yahoo 和 FRED；任一失败后按现有 1秒、2秒退避重试。只对 `^NDX` 增加一个 CSV 请求，工作流 10 分钟超时和报告发送次数不变。

## 文档

README 的数据来源说明改为：一般行情使用 Yahoo Finance；纳指使用 Yahoo 当天值并由 FRED/Nasdaq 官方日线补齐历史。失败规则明确说明官方历史不可用时不计算纳指涨跌。

## 测试与验收

- FRED 解析：有效 CSV 转成日期映射，`.` 行忽略，无效/空响应安全失败。
- 计算回归：Yahoo 缺 7月24日、FRED 提供该日时，日涨跌为 `-89.13（-0.32%）`，5日与20日窗口使用完整序列。
- 编排：`^NDX` 调用 FRED；其他 symbol 不调用；FRED 失败时纳指返回安全错误。
- 兼容：已有正常 Yahoo 行情计算不变，其他五个标的不增加依赖。
- 全量运行 pytest、Ruff、Python 编译、YAML 解析、Secret 扫描和 `git diff --check`。
- 不手动触发 Server酱或真实 DeepSeek 请求。
