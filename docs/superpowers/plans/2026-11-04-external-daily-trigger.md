# External Daily Trigger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the selected free external trigger approach for daily reports before 07:00 Asia/Shanghai.

**Architecture:** cron-job.org dispatches the existing workflows at 06:40 and 06:50. A standard-library Python guard checks daily success artifacts before sending; workflow concurrency serializes triggers and successful send steps publish receipts. Existing early-morning native schedules remain as fallback to avoid delaying delivery before external activation.

**Tech Stack:** Python 3.12+, pytest, GitHub Actions, artifacts REST API, cron-job.org.

**Spec:** docs/superpowers/specs/2026-11-04-external-daily-trigger-design.md

## Global Constraints

- Keep existing report generation and secrets unchanged.
- No live notification tests and no secrets in files or logs.
- Only send from the repository default branch.
- Guard errors must stop delivery; do not infer that no receipt exists.
- Use Asia/Shanghai for the delivery date; each report has independent state.
- Keep contents: read and add only actions: read for receipt checks.
- External account setup and end-to-end timing remain a user activation step.

## Review Focus

- Receipt upload failure after successful send can cause a later duplicate; document the limit.
- GitHub dispatch acceptance is not proof of notification success; explain activation verification.
- Concurrent external/native triggers must share a concurrency group.
- Expired and untrusted branch/repository artifacts must not suppress delivery.
- Fully failed upstream data currently sends a failure summary then exits nonzero; this remains eligible for retry.

### Task 1: External triggers with daily receipt checks

**Files:**
- Create: technews/delivery_guard.py, tests/test_delivery_guard.py
- Modify: .github/workflows/daily_news.yml, .github/workflows/daily_finance.yml, tests/test_workflows.py, .gitignore, README.md
- Create: docs/external-scheduler.md, docs/cron-job-examples.json

**Interfaces:**
- `prepare_delivery(report: str, repository: str, token: str, default_branch: str, *, now: datetime | None = None, opener=urlopen) -> tuple[bool, str]` checks today's named receipt using GitHub artifacts API and returns should_send and marker_name.
- `main() -> int` accepts positional report news/finance, reads GitHub context, writes GITHUB_OUTPUT and a secret-free receipt file when delivery is allowed, returns nonzero on errors.

- [x] Write behavior tests for timezone rollover, independent reports, trusted live receipts, ignored expired/foreign receipts, API failure and command outputs.
- [x] Run new tests RED; confirm the missing guard causes failure.
- [x] Implement the standard-library guard with bounded API timeout and safe errors.
- [x] Run guard tests GREEN.
- [x] Replace old workflow tests that pin previous schedules with parsed workflow contract tests; add YAML as a development-only dependency if needed.
- [x] Keep existing early native schedules, add main-branch restriction, receipt guard before dependencies, send-step gating, successful-send-only artifact upload with retention-days: 7.
- [x] Write the specific 06:40/06:50 cron-job.org setup guide and secret-free JSON examples for this repository; revise README timing.
- [x] Run complete pytest, Ruff lint/format, git diff --check, and inspect workflow conditions and docs against examples.
- [x] Commit, obtain one independent whole-change review, and address significant findings with tests.
- [x] Publish a reviewable branch/PR if connection permissions allow; otherwise produce a patch and source bundle in outputs. Do not merge or activate external scheduling automatically.

## Delivery status

The initial connection rejected branch creation with HTTP 403. The user subsequently installed the official GitHub connector and granted this repository access, enabling publication of the verified change for review and Python 3.12 CI. External cron-job.org account activation and real message arrival verification remain a user setup step; no schedule or live notification has been activated during implementation.
