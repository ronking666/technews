# Reliable Daily Push Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver dependable, independent ServerChan technology and finance reports at 05:30 and 06:15 Asia/Shanghai.

**Architecture:** Keep the two root scripts as orchestration entry points and move reusable network, parsing, market and notification behavior into a focused `technews` package. Each upstream produces a structured result so partial failure can be reported while total failure and notification failure return non-zero exit codes.

**Tech Stack:** Python 3.12, requests 2.34.2, yfinance 1.5.1, pytest 9.1.1, GitHub Actions.

## Global Constraints

- Technology news runs at 05:30 Asia/Shanghai; finance runs at 06:15 Asia/Shanghai.
- The two workflows remain independent.
- Partial upstream failure sends available content and identifies failed inputs.
- Total upstream failure attempts a failure-summary push and exits non-zero.
- Missing credentials and ServerChan failures exit non-zero without exposing the send key.
- Retry only safe GET operations automatically; never automatically retry the notification POST.
- All direct network operations have bounded timeouts or attempt limits.

---

### Task 1: Shared configuration, HTTP session and notifier

**Files:**
- Create: `technews/__init__.py`
- Create: `technews/config.py`
- Create: `technews/http.py`
- Create: `technews/notifier.py`
- Create: `tests/test_http.py`
- Create: `tests/test_notifier.py`

**Interfaces:**
- Produces: `APP_TIMEZONE`, `REQUEST_TIMEOUT`, `RSS_SOURCES`, `MARKET_TICKERS`.
- Produces: `create_retrying_session() -> requests.Session`.
- Produces: `NotificationError` and `send_to_serverchan(sendkey, title, content, post=requests.post) -> None`.

- [ ] **Step 1: Write failing retry and notifier tests**

```python
def test_retry_session_retries_get_but_not_post():
    adapter = create_retrying_session().get_adapter("https://")
    assert adapter.max_retries.total == 3
    assert adapter.max_retries.allowed_methods == frozenset({"GET"})

def test_notifier_accepts_serverchan_success(fake_response):
    fake_response.json.return_value = {"code": 0}
    send_to_serverchan("secret", "title", "body", post=lambda *a, **k: fake_response)

def test_notifier_redacts_secret_from_transport_failure():
    def fail(*args, **kwargs):
        raise requests.RequestException("https://sctapi.ftqq.com/secret.send")
    with pytest.raises(NotificationError) as error:
        send_to_serverchan("secret", "title", "body", post=fail)
    assert "secret" not in str(error.value)
```

- [ ] **Step 2: Run the focused tests and verify import failures**

Run: `python -m pytest tests/test_http.py tests/test_notifier.py -q`

Expected: FAIL because the `technews` modules do not exist.

- [ ] **Step 3: Implement the shared modules**

```python
# technews/http.py
def create_retrying_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session

# technews/notifier.py
def send_to_serverchan(sendkey, title, content, post=requests.post) -> None:
    if not sendkey or not sendkey.strip():
        raise NotificationError("SERVERCHAN_SENDKEY is missing")
    try:
        response = post(
            f"https://sctapi.ftqq.com/{sendkey}.send",
            data={"title": title, "desp": content},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        raise NotificationError("ServerChan request failed") from None
    if str(result.get("code")) != "0":
        raise NotificationError("ServerChan rejected the message")
```

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_http.py tests/test_notifier.py -q`

Expected: all focused tests PASS.

- [ ] **Step 5: Commit the shared foundation**

```bash
git add technews tests/test_http.py tests/test_notifier.py
git commit -m "refactor: add reliable network and notification foundation"
```

### Task 2: RSS pipeline and technology entry point

**Files:**
- Create: `technews/rss.py`
- Create: `tests/test_rss.py`
- Create: `tests/test_main.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: `RSS_SOURCES`, `REQUEST_TIMEOUT`, `APP_TIMEZONE`, `create_retrying_session`, `send_to_serverchan`.
- Produces: `NewsItem`, `NewsSourceResult`, `parse_rss`, `fetch_news_source`, `render_news_report`.
- Produces: `main.run(sendkey, now=None, session=None, notifier=send_to_serverchan) -> int`.

- [ ] **Step 1: Write failing parser and orchestration tests**

```python
def test_parse_rss_sanitizes_titles_and_rejects_unsafe_links():
    xml = b"<rss><channel><item><title>A &amp; B</title><link>javascript:bad</link></item></channel></rss>"
    assert parse_rss(xml, limit=3) == (NewsItem("A & B", ""),)

def test_partial_news_failure_still_sends(monkeypatch):
    results = [
        NewsSourceResult("IT之家", (NewsItem("News", "https://example.com"),)),
        NewsSourceResult("备用源", error="request failed"),
    ]
    sent = []
    code = run("key", results=results, notifier=lambda key, title, body: sent.append(body))
    assert code == 0
    assert "IT之家" in sent[0] and "备用源" in sent[0]

def test_total_news_failure_pushes_summary_and_fails():
    results = [NewsSourceResult("IT之家", error="request failed")]
    sent = []
    assert run("key", results=results, notifier=lambda *args: sent.append(args)) == 1
    assert sent
```

- [ ] **Step 2: Run tests and verify missing behavior**

Run: `python -m pytest tests/test_rss.py tests/test_main.py -q`

Expected: FAIL because RSS result types and the new `run` interface do not exist.

- [ ] **Step 3: Implement structured RSS behavior and the thin entry point**

```python
@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str = ""

@dataclass(frozen=True)
class NewsSourceResult:
    name: str
    items: tuple[NewsItem, ...] = ()
    error: str | None = None

def fetch_news_source(session, name, url, limit=8) -> NewsSourceResult:
    try:
        response = session.get(url, headers=RSS_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        items = parse_rss(response.content, limit)
        return NewsSourceResult(name, items) if items else NewsSourceResult(name, error="未返回新闻")
    except (requests.RequestException, ET.ParseError, ValueError):
        return NewsSourceResult(name, error="获取失败")

def run(sendkey, now=None, session=None, notifier=send_to_serverchan, results=None) -> int:
    if not sendkey:
        print("错误：未配置 SERVERCHAN_SENDKEY。")
        return 2
    now = now or datetime.now(APP_TIMEZONE)
    results = results or collect_configured_news(session or create_retrying_session())
    content = render_news_report(results)
    try:
        notifier(sendkey, f"📰 每日科技资讯早报 ({now:%Y年%m月%d日})", content)
    except NotificationError as error:
        print(f"推送失败：{error}")
        return 1
    return 0 if any(result.items for result in results) else 1
```

- [ ] **Step 4: Run RSS and entry-point tests**

Run: `python -m pytest tests/test_rss.py tests/test_main.py -q`

Expected: all focused tests PASS.

- [ ] **Step 5: Commit the technology pipeline**

```bash
git add main.py technews/rss.py tests/test_rss.py tests/test_main.py
git commit -m "feat: make technology push resilient"
```

### Task 3: Market pipeline and finance entry point

**Files:**
- Create: `technews/market.py`
- Create: `tests/test_market.py`
- Create: `tests/test_finance.py`
- Modify: `finance.py`

**Interfaces:**
- Consumes: `MARKET_TICKERS`, `APP_TIMEZONE`, `send_to_serverchan`.
- Produces: `MarketResult`, `market_result_from_history`, `fetch_market_result`, `render_market_report`.
- Produces: `finance.run(sendkey, now=None, notifier=send_to_serverchan, results=None) -> int`.

- [ ] **Step 1: Write failing market and orchestration tests**

```python
def test_market_result_calculates_change_and_date():
    frame = pd.DataFrame(
        {"Close": [100.0, 103.0]},
        index=pd.to_datetime(["2026-07-14", "2026-07-15"]),
    )
    result = market_result_from_history("指数", "IDX", frame)
    assert result.current == 103.0
    assert result.change == 3.0
    assert result.pct_change == pytest.approx(3.0)
    assert result.data_date == date(2026, 7, 15)

def test_partial_market_failure_still_sends():
    results = [
        MarketResult("指数", "IDX", 103, 3, 3, date(2026, 7, 15)),
        MarketResult("黄金", "GC=F", error="获取失败"),
    ]
    sent = []
    assert run("key", results=results, notifier=lambda key, title, body: sent.append(body)) == 0
    assert "数据日期" in sent[0] and "获取失败" in sent[0]

def test_total_market_failure_pushes_summary_and_fails():
    results = [MarketResult("指数", "IDX", error="获取失败")]
    sent = []
    assert run("key", results=results, notifier=lambda *args: sent.append(args)) == 1
```

- [ ] **Step 2: Run tests and verify missing behavior**

Run: `python -m pytest tests/test_market.py tests/test_finance.py -q`

Expected: FAIL because the market module and new finance interface do not exist.

- [ ] **Step 3: Implement bounded market retrieval and finance orchestration**

```python
@dataclass(frozen=True)
class MarketResult:
    name: str
    symbol: str
    current: float | None = None
    change: float | None = None
    pct_change: float | None = None
    data_date: date | None = None
    error: str | None = None

def fetch_market_result(name, symbol, ticker_factory=yf.Ticker, attempts=3, pause=time.sleep):
    for attempt in range(attempts):
        try:
            history = ticker_factory(symbol).history(period="7d", timeout=15)
            return market_result_from_history(name, symbol, history)
        except Exception:
            if attempt + 1 < attempts:
                pause(1.0 * (attempt + 1))
    return MarketResult(name, symbol, error="获取失败")

def run(sendkey, now=None, notifier=send_to_serverchan, results=None) -> int:
    if not sendkey:
        print("错误：未配置 SERVERCHAN_SENDKEY。")
        return 2
    now = now or datetime.now(APP_TIMEZONE)
    results = results or collect_configured_markets()
    content = render_market_report(results)
    try:
        notifier(sendkey, f"📊 每日财经与金属行情早报 ({now:%Y年%m月%d日})", content)
    except NotificationError as error:
        print(f"推送失败：{error}")
        return 1
    return 0 if any(result.error is None for result in results) else 1
```

- [ ] **Step 4: Run market and finance tests**

Run: `python -m pytest tests/test_market.py tests/test_finance.py -q`

Expected: all focused tests PASS.

- [ ] **Step 5: Commit the finance pipeline**

```bash
git add finance.py technews/market.py tests/test_market.py tests/test_finance.py
git commit -m "feat: make finance push resilient"
```

### Task 4: Reproducible workflows, repository hygiene and verification

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `README.md`
- Create: `.github/workflows/ci.yml`
- Modify: `.github/workflows/daily_news.yml`
- Modify: `.github/workflows/daily_finance.yml`
- Create: `tests/test_workflows.py`
- Delete: `Morning-Report`

**Interfaces:**
- Scheduled entry points remain `python main.py` and `python finance.py`.
- CI command is `python -m pytest -q`.

- [ ] **Step 1: Add failing workflow configuration tests**

```python
def test_news_schedule_is_0530_shanghai():
    assert "cron: '30 21 * * *'" in Path(".github/workflows/daily_news.yml").read_text("utf-8")

def test_finance_schedule_is_0615_shanghai():
    assert "cron: '15 22 * * *'" in Path(".github/workflows/daily_finance.yml").read_text("utf-8")

def test_workflows_use_requirements_and_least_privilege():
    for path in ("daily_news.yml", "daily_finance.yml"):
        text = Path(".github/workflows", path).read_text("utf-8")
        assert "permissions:\n  contents: read" in text
        assert "pip install -r requirements.txt" in text
        assert "timeout-minutes: 10" in text
```

- [ ] **Step 2: Run workflow tests and verify they fail**

Run: `python -m pytest tests/test_workflows.py -q`

Expected: FAIL on old cron expressions and missing hardening.

- [ ] **Step 3: Update dependencies and workflows**

```text
# requirements.txt
requests==2.34.2
yfinance==1.5.1

# requirements-dev.txt
pytest==9.1.1
```

Both scheduled workflows must contain `permissions: contents: read`, a stable concurrency group, `timeout-minutes: 10`, Python 3.12 with pip caching, `pip install -r requirements.txt`, and the exact cron expressions asserted above. CI installs both requirements files and runs `python -m pytest -q` on push and pull request.

- [ ] **Step 4: Add concise public documentation and remove dead code**

Document purpose, schedules, `SERVERCHAN_SENDKEY` setup, manual workflow dispatch, failure semantics, local test commands and the personal-use status of yfinance data in `README.md`. Ignore Python caches and virtual environments in `.gitignore`. Delete `Morning-Report` because no active workflow calls it.

- [ ] **Step 5: Run all verification commands**

Run: `python -m pytest -q`

Expected: all tests PASS.

Run: `python -m compileall -q main.py finance.py technews tests`

Expected: exit code 0.

Run: `git diff --check`

Expected: exit code 0 and no output.

- [ ] **Step 6: Commit the workflows and documentation**

```bash
git add .github .gitignore README.md requirements.txt requirements-dev.txt tests/test_workflows.py Morning-Report
git commit -m "ci: schedule and verify reliable daily pushes"
```
