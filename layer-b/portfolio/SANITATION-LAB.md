# Project 011 — synthetic sanitation service

## Delivered scope

The local application includes fictional route registration, scheduled service runs, cumulative service observations, current-record verification, recovery/correction records, and anonymous missed-service reports with response and reopening history. This is a prototype derived from the [editorial project plan](plans/011.md); the linked source document has not been read. Actual service rules and institutional acceptance remain unresolved.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/sanitation>. Restart an existing server to add the routes and tables. Existing portfolio, permit and maintenance records are retained. No sample records are inserted automatically.

## Fictional walkthrough

1. Enter an operator identifier. Register route `SYN-ROUTE-001`, stream TRASH, area `Demo area`, expected stop-visits 10, timestamp `2026-01-01T00:00:00Z`, with fictional scenario evidence.
2. Schedule run `SYN-RUN-001` at `2026-01-01T01:00:00Z`. The expected stop-visit denominator is copied from the route.
3. Record STARTED at `2026-01-01T02:00:00Z`. The count is unknown at this stage.
4. Record SERVICE_RECORDED at `2026-01-01T03:00:00Z` with cumulative served count 8 and explicit evidence. This is an unverified record, so it is excluded from the verified missed-service rate.
5. Use a distinct verifier identifier to record observed count 8 at `2026-01-01T04:00:00Z`. Matching counts tied to the current record give a verified shortfall: 2 missed stop-visits / 10 expected stop-visits = 20%.
6. Create anonymous report `SYN-REPORT-001` for that run at `04:00:00Z`, using a fictional non-identifying description. Record report resolution at `05:00:00Z` with response evidence. This one-hour response record does not establish that service was restored.
7. Record CORRECTION_RECORDED at `05:00:00Z` with cumulative served count 10. This replaces the current asserted total, not an incremental count; prior records stay in history. Verification becomes stale even if timestamps are identical.
8. Record observed count 10 at `06:00:00Z` with a distinct verifier. At cutoff `2026-01-02T00:00:00Z`, the verified missed-service rate is 0%, the verified recovery interval is three hours from the first shortfall to the latest matching current-record check, and report-response time is one hour.
9. Reopen the anonymous report at `07:00:00Z` with new evidence. The report is open and its repeat-report count increases, while route service totals remain unchanged.

All identifiers start `SYN-`; times require RFC3339 UTC/offset values. Counts must be explicit integers within the scheduled denominator, including zero when observed. Service events/checks are nondecreasing. New service totals may revise counts upward or downward with rationale. Every revision requires a fresh check tied to its event sequence. Expected version numbers reject stale writes. Distinct verifier identifiers are a separation rule, not proof of authenticated independent identity or observation.

## Measurement contract

| Measure | Definition and limits |
| --- | --- |
| Verified missed-service rate | Sum of expected minus served stop-visits / expected stop-visits across runs with matching checks for their latest record at cutoff |
| Denominator | Scheduled stop-visits for verified runs; not unique households or residents. Unverified and not-yet-recorded runs are reported separately |
| Verification mismatch | Observed count differs from the recorded total; that run remains excluded until a current matching check is recorded |
| Verified recovery hours | First recorded shortfall to latest matching check for a currently complete run; includes queue, revision and verification delay. Null if no eligible recovered run |
| Correction records | Count of cumulative service-total revisions, not a count of physical recovery trips |
| Anonymous reports | Separate observations linked to a run; duplicates may exist and never supply the rate denominator |
| Resolved-report hours | Original report to latest recorded resolution for reports resolved at cutoff; reopening removes the report from this closed sample |
| Open-report age | Original report to cutoff for unresolved reports, including reopened reports; separately censored |
| Repeat-report events | Transitions from resolved back to open; not a unique household or verified repeat-defect rate |

Historical reports apply cutoff before selecting current events and checks. Exact area and stream filters can isolate comparable runs. Empty rates/statistics remain null with explicit sample sizes; medians and nearest-rank P90 are descriptive synthetic statistics. Mixing routes or streams requires confirming comparability. Historical event times are operator-supplied scenario times, not the time of data entry. No causal effects, real-world reliability or independent inspection findings are inferred.

## Privacy and operating boundary

The structured model contains no household name, address, contact information or per-stop identifiers. Enter only fictional non-identifying text in evidence and report fields; free-text fields are not a redaction system. Source/reviewer identifiers remain local assertions. No actual collection, resident communication, dispatch, payment, procurement or service decision occurs. Low complaint counts never establish complete service or absence of reporting barriers.

## Interfaces and persistence

- `GET /api/sanitation` returns routes, runs and anonymous reports.
- `POST /api/sanitation/routes` registers a fictional route.
- `POST /api/sanitation/runs` schedules a run.
- `POST /api/sanitation/runs/{id}/events` records start, service or revised cumulative total.
- `POST /api/sanitation/runs/{id}/checks` records a current-event count check.
- `POST /api/sanitation/issues` opens an anonymous report.
- `POST /api/sanitation/issues/{id}/events` resolves or reopens a report with evidence.
- `GET /api/sanitation/report?as_of=...&area=...&stream=...` computes historical measures.

The shared loopback-only server protects mutation routes with its local token and host/origin checks. Full JSON export and SQLite backup include all service/check/report histories and audit records. See [backup/restore](APPLICATION.md#export-backup-and-restore).

## Outstanding acceptance

Import and review the full project source; define actual route scope, schedules, denominator rules, accessible reporting channels, privacy/retention controls, escalation responsibilities and qualified verification. Obtain institutional acceptance before any real operation. The prototype does not mark project 011 complete and does not alter the original Layer A hold or pinned synthetic permit packet.
