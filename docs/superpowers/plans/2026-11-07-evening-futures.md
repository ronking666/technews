# Evening Futures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate 20:30 Beijing Nasdaq-100 futures WeChat report.
**Architecture:** Bounded Yahoo chart metadata collection, deterministic Markdown, existing notifier and daily receipt guard. A third workflow and scheduler example deploy independently of morning reports.
**Tech Stack:** Python 3.12+, curl_cffi, pytest, Ruff, GitHub Actions.
**Spec:** ../specs/2026-11-07-evening-futures.md

## Global Constraints

- No new provider credentials or AI calls. Preserve both morning workflows.
- Default six symbols; Asia/Shanghai; stale threshold 120 minutes; request timeout 15 seconds, two attempts per symbol.
- Missing values remain unavailable; quote time is mandatory; NQ cannot be substituted with a cash index.

## Review Focus

- A weekend quote remains dated and marked stale.
- Invalid or future timestamps do not become current prices.
- Malformed/empty upstream payloads do not suppress valid related quotes.
- Failed sends never save a success receipt; futures receipts do not block finance.
- External settings remain explicitly pending until saved in the service.

### Task 1: Quote collection and report

**Files:** Create technews/quotes.py, tests/test_quotes.py. Modify settings.py, config.py, config.toml, requirements.txt.
**Interfaces:** collect_configured_quotes() -> tuple[QuoteResult, ...]; render_quote_report(results, now, max_age_minutes=120) -> str; QuoteResult contains name, symbol, quote or error.

- [ ] Write tests for metadata parsing, safe numbers, symbol/type/time validation, bounded retries, partial failure, stale rendering and optional config defaults; run and observe failures.
- [ ] Implement frozen quote/result records, bounded chart requests, strict metadata parsing and readable Chinese report.
- [ ] Run targeted tests and full suite; commit.

### Task 2: Delivery and deployment

**Files:** Create futures.py, tests/test_futures.py, daily_futures.yml. Modify delivery_guard.py, workflow/guard tests, README.md and scheduler docs/examples.
**Interfaces:** run(sendkey, now=None, notifier=..., results=None) -> int; CLI --preview never calls notifier.

- [ ] Write failing tests for missing key, notifier failure, partial/all-data failure, preview and independent receipts; add parsed workflow contracts.
- [ ] Implement entry point, independent receipt kind and 20:30 workflow; document 20:30/20:40 external trigger.
- [ ] Run full tests, Ruff and live read-only preview; independently review once, fix meaningful findings, publish PR and inspect CI.
- [ ] Integrate authorized change and verify default branch; complete or identify the exact remaining external-service setting.
