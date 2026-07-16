# Reliable Daily Push Design

## Goal

Make the public `ronking666/technews` repository deliver two dependable daily ServerChan messages:

- technology news at 05:30 Asia/Shanghai;
- finance and metals data at 06:15 Asia/Shanghai.

The two messages remain independent so a failure in one pipeline cannot block the other.

## Success criteria

1. Every scheduled workflow uses an explicit UTC cron corresponding to the required Asia/Shanghai time.
2. Report titles and displayed dates use `Asia/Shanghai`, independent of the GitHub runner timezone.
3. A partial upstream failure still sends the available content and identifies failed sources or symbols.
4. If every upstream source fails, the script attempts to send a failure summary and then exits non-zero.
5. A missing secret or failed ServerChan request exits non-zero without printing the secret-bearing URL.
6. Network operations have bounded timeouts and retry only operations that are safe to repeat.
7. Automated tests cover formatting, partial failure, total failure, timezone handling, and notifier responses.
8. Dependencies are version-constrained and installed from a single requirements file in both workflows.

## Architecture

Keep `main.py` and `finance.py` as small independent entry points. Move reusable logic into a `technews` package:

- `config.py`: timezone, RSS sources, market symbols, timeout and retry settings;
- `http.py`: a configured `requests.Session` for retryable GET requests;
- `rss.py`: RSS retrieval, parsing, sanitization and per-source result objects;
- `market.py`: market retrieval, price-change calculation and per-symbol result objects;
- `notifier.py`: ServerChan request construction and strict response validation.

Each source operation returns structured success or failure data. Entry points decide whether the run is partially successful or totally failed, build the Markdown report, call the notifier once, and return a meaningful process exit code.

The unused `Morning-Report` script is removed because its workflow was deleted and its functionality overlaps the active news pipeline.

## Data flow

### Technology news

1. The workflow starts `main.py` at 21:30 UTC, which is 05:30 Asia/Shanghai.
2. The entry point validates `SERVERCHAN_SENDKEY`.
3. Each configured RSS source is fetched independently with timeouts and bounded GET retries.
4. Parsed items are sanitized and formatted; failed sources become clearly labeled report sections.
5. If at least one source succeeds, the report is pushed and the run succeeds.
6. If all sources fail, a failure summary is pushed when possible and the run exits non-zero.

### Finance data

1. The workflow starts `finance.py` at 22:15 UTC, which is 06:15 Asia/Shanghai.
2. The entry point validates `SERVERCHAN_SENDKEY`.
3. Each configured symbol is queried independently with bounded attempts.
4. Successful sections include the latest available trading date, price and day-over-day change; failures are labeled.
5. Partial success is pushed as a normal report. Total source failure still produces a failure summary and a non-zero exit.

## Error handling and security

- GET requests retry connection errors, rate limits and transient 5xx responses with backoff.
- ServerChan POST is not automatically retried because a retry could create duplicate messages.
- Every direct network call has a timeout or bounded attempt policy.
- The notifier converts transport and API failures into safe error messages that do not contain the request URL or send key.
- Entry points log source names and failure categories, not credentials.
- Workflow permissions are reduced to `contents: read`, and jobs have a maximum runtime and concurrency group.

## Workflows and dependencies

Update the two scheduled workflows to use the new UTC schedules, one requirements file, pip caching, least-privilege permissions, job timeouts and concurrency protection. Add a CI workflow for pushes and pull requests that installs the same dependencies and runs the test suite.

Runtime dependency versions will be constrained to known-compatible release lines rather than installing unconstrained latest packages. Test-only dependencies remain separate.

## Testing

Tests use fixtures and mocks; they do not call live RSS, Yahoo Finance or ServerChan services.

Coverage includes:

- valid, empty and malformed RSS payloads;
- text sanitization and safe links;
- positive, negative and unchanged market calculations;
- partial and total upstream failure decisions;
- successful and rejected ServerChan responses;
- credential-safe exception messages;
- Asia/Shanghai date formatting;
- the intended workflow cron expressions.

Before publishing, run the full test suite, Python compilation checks and a clean working-tree diff review. Live delivery still depends on the existing repository secret and upstream service availability; the workflows will make those failures explicit instead of reporting false success.
