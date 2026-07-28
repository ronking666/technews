# NDX Data Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 FRED/Nasdaq 官方历史收盘补齐 Yahoo `^NDX` 缺失日线，防止把非相邻交易日误报为“当日涨跌”。

**Architecture:** 新增只负责 FRED CSV 的小型 provider；行情计算把 Yahoo 和 FRED 转成按日期排序的收盘观测，Yahoo 有效值优先、FRED 只补空缺。只有 `^NDX` 使用官方历史补齐，官方源失败时该标的 fail closed，其他五个标的保持原样。

**Tech Stack:** Python 3.12、requests、csv、yfinance、pandas、pytest、Ruff

## Global Constraints

- Yahoo 继续提供及时的 `^NDX` 当天收盘。
- FRED `NASDAQ100` 只补齐历史缺失值，不覆盖 Yahoo 有效值。
- FRED 不可用时不得用未经校验的 Yahoo 数据计算纳指涨跌。
- 其他五个行情标的不请求 FRED。
- 不增加 API Key、第三方 SDK、Server酱发送次数或工作流权限。
- 不执行真实 Server酱或 DeepSeek 请求。

---

### Task 1: FRED CSV 数据提供器

**Files:**
- Create: `technews/fred.py`
- Create: `tests/test_fred.py`

**Interfaces:**
- Produces: `MarketDataError(RuntimeError)`
- Produces: `fetch_fred_closes(series_id: str, start: date, end: date, *, get: Callable[..., Any] = requests.get) -> dict[date, float]`

- [ ] **Step 1: Write failing parser tests**

在 `tests/test_fred.py` 创建有效响应测试：

```python
from datetime import date
from unittest.mock import Mock


def test_fetch_fred_closes_parses_values_and_skips_missing_rows():
    from technews.fred import fetch_fred_closes

    response = Mock()
    response.text = (
        "observation_date,NASDAQ100\n"
        "2026-07-23,28454.81\n"
        "2026-07-24,28128.34\n"
        "2026-07-27,.\n"
    )
    get = Mock(return_value=response)

    result = fetch_fred_closes(
        "NASDAQ100",
        date(2026, 7, 23),
        date(2026, 7, 27),
        get=get,
    )

    assert result == {
        date(2026, 7, 23): 28454.81,
        date(2026, 7, 24): 28128.34,
    }
    assert get.call_args.kwargs["params"] == {
        "id": "NASDAQ100",
        "cosd": "2026-07-23",
        "coed": "2026-07-27",
    }
```

再增加无效列、无有效数值和 `requests.RequestException` 三种测试，均断言抛出 `MarketDataError`，且错误文本不包含模拟响应正文或上游异常详情。

- [ ] **Step 2: Run tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_fred.py -q`

Expected: FAIL with `ModuleNotFoundError: technews.fred`.

- [ ] **Step 3: Implement the minimal provider**

`technews/fred.py` 使用以下结构：

```python
import csv
import math
from collections.abc import Callable
from datetime import date
from io import StringIO
from typing import Any

import requests

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


class MarketDataError(RuntimeError):
    pass


def fetch_fred_closes(series_id, start, end, *, get=requests.get):
    try:
        response = get(
            FRED_CSV_URL,
            params={"id": series_id, "cosd": start.isoformat(), "coed": end.isoformat()},
            headers={"User-Agent": "technews-daily-report/1.0"},
            timeout=(5, 20),
        )
        response.raise_for_status()
        reader = csv.DictReader(StringIO(response.text))
        if not reader.fieldnames or "observation_date" not in reader.fieldnames or series_id not in reader.fieldnames:
            raise ValueError
        closes = {}
        for row in reader:
            try:
                observed = date.fromisoformat(row["observation_date"])
                value = float(row[series_id])
            except (TypeError, ValueError):
                continue
            if math.isfinite(value):
                closes[observed] = value
        if not closes:
            raise ValueError
        return closes
    except (requests.RequestException, ValueError, csv.Error):
        raise MarketDataError("Official market history is unavailable") from None
```

- [ ] **Step 4: Run tests and commit**

Run: `.venv\Scripts\python.exe -m pytest tests/test_fred.py -q`

Expected: PASS.

```bash
git add technews/fred.py tests/test_fred.py
git commit -m "feat: add FRED market history provider"
```

---

### Task 2: NDX 历史合并与 fail-closed 行为

**Files:**
- Modify: `technews/market.py`
- Modify: `tests/test_market.py`

**Interfaces:**
- Consumes: `fetch_fred_closes(series_id, start, end) -> dict[date, float]`
- Extends: `market_result_from_history(..., fallback_closes: Mapping[date, float] | None = None) -> MarketResult`
- Extends: `fetch_market_result(..., official_history_loader: Callable[[str, date, date], Mapping[date, float]] = fetch_fred_closes) -> MarketResult`
- Produces: `OFFICIAL_HISTORY_SERIES = {"^NDX": "NASDAQ100"}`

- [ ] **Step 1: Write the failing missing-day regression test**

使用 Yahoo 缺少 7月24日的数据构造 DataFrame，并提供 FRED fallback：

```python
def test_market_result_fills_missing_ndx_close_before_calculating_change():
    from technews.market import market_result_from_history

    frame = pd.DataFrame(
        {"Close": [28592.66, 28604.23, 29155.18, 28998.10, 28454.81, 28039.21]},
        index=pd.to_datetime([
            "2026-07-17", "2026-07-20", "2026-07-21",
            "2026-07-22", "2026-07-23", "2026-07-27",
        ]),
    )

    result = market_result_from_history(
        "纳斯达克100指数",
        "^NDX",
        frame,
        trend_windows=(5,),
        range_days=5,
        fallback_closes={date(2026, 7, 24): 28128.34},
    )

    assert result.change == pytest.approx(-89.13)
    assert result.pct_change == pytest.approx(-0.316866, rel=1e-5)
    window, value = result.trend_returns[0]
    assert window == 5
    assert value == pytest.approx((28039.21 / 28604.23 - 1) * 100)
```

- [ ] **Step 2: Write orchestration and failure tests**

新增三个测试：

1. `^NDX` 调用 `official_history_loader("NASDAQ100", start, end)`，缺失日补齐后得到正确日涨跌。
2. loader 抛出 `MarketDataError` 时，`attempts=1` 返回 `MarketResult(error="获取失败")`。
3. symbol 为 `GC=F` 时 loader 即使设置为抛错函数也不被调用，Yahoo 结果正常返回。

- [ ] **Step 3: Run tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_market.py -q`

Expected: FAIL because `fallback_closes` and `official_history_loader` do not exist.

- [ ] **Step 4: Implement date-keyed close merging**

在 `market_result_from_history` 中：

```python
observations: dict[date, float] = {}
for index, raw_value in history["Close"].items():
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        continue
    observed = index.date() if hasattr(index, "date") else index
    if isinstance(observed, date) and math.isfinite(value):
        observations[observed] = value

for observed, value in (fallback_closes or {}).items():
    if isinstance(observed, date) and math.isfinite(float(value)):
        observations.setdefault(observed, float(value))

ordered = sorted(observations.items())
```

后续 previous/current、日期、趋势和区间均从 `ordered` 计算，保持现有公式与输出字段。

- [ ] **Step 5: Implement NDX official history loading**

在 `fetch_market_result` 获取 Yahoo history 后：

```python
fallback_closes = None
series_id = OFFICIAL_HISTORY_SERIES.get(symbol)
if series_id is not None:
    valid_closes = history["Close"].dropna()
    if len(valid_closes) < 2:
        raise ValueError("Insufficient market history")
    start = valid_closes.index[0].date()
    end = valid_closes.index[-1].date()
    fallback_closes = official_history_loader(series_id, start, end)
return market_result_from_history(
    name,
    symbol,
    history,
    fallback_closes=fallback_closes,
)
```

- [ ] **Step 6: Run market and entry tests, then commit**

Run: `.venv\Scripts\python.exe -m pytest tests/test_market.py tests/test_finance.py -q`

Expected: PASS.

```bash
git add technews/market.py tests/test_market.py
git commit -m "fix: backfill missing NDX market history"
```

---

### Task 3: 文档、全量验证与发布

**Files:**
- Modify: `README.md`
- Verify: all changed files

**Interfaces:**
- Documents: Yahoo current value + FRED/Nasdaq historical backfill and fail-closed behavior.

- [ ] **Step 1: Update README**

在“失败规则”和“数据来源与免责声明”中说明：纳指使用 Yahoo 当天值和 FRED/Nasdaq 官方历史补齐；官方历史不可用时该标的不计算涨跌，其他标的继续发送。

- [ ] **Step 2: Run the complete verification suite**

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m compileall -q main.py finance.py technews
```

Expected: all commands exit 0.

- [ ] **Step 3: Run repository safety checks**

解析全部工作流 YAML，扫描疑似 Secret，运行 `git diff --check`，确认工作流、推送时间和 Secret 配置没有变化。

- [ ] **Step 4: Commit documentation**

```bash
git add README.md
git commit -m "docs: explain NDX official history fallback"
```

- [ ] **Step 5: Publish and confirm**

Push `HEAD:main`，等待 push CI 成功，确认本地 HEAD 与远端 `main` 相同且工作树干净。不手动触发财经或科技推送工作流。
