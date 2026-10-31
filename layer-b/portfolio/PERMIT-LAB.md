# Project 009 — synthetic permit workflow

## Delivered behavior

The application now includes a project-specific executable prototype based on the supplied [synthetic permit scenario](../examples/permit/README.md), not the unread linked Google Doc. It records fictional cases, an append-only stage history, correction cycles, synthetic quality-review records and reproducible measurements. Each case is explicitly `SYNTHETIC`; no permit is issued and no government decision is made.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/permits>. No sample cases or measurements are inserted automatically. Existing workspaces acquire the new tables when the application starts; projects and source records are preserved.

## Try a fictional case

1. Enter your identifier. Create case `SYN-DEMO-001`, category `Fictional permit`, receipt `2026-01-01T00:00:00Z`, with a clearly fictional scenario reference.
2. Record `IN_REVIEW` at `2026-01-01T01:00:00Z`.
3. Record `AWAITING_CORRECTION` at `2026-01-01T02:00:00Z`.
4. Record `IN_REVIEW` at `2026-01-01T03:00:00Z`.
5. Record `INSPECTION` at `2026-01-01T04:00:00Z`.
6. Record `DECIDED` at `2026-01-01T10:00:00Z`. This is a fictional recorded decision stage, not an approval action.
7. Add a quality review at `2026-01-01T11:00:00Z` with explicit test criteria and a recorded pass/fail result.
8. Set the report cutoff to `2026-01-02T00:00:00Z` and refresh. With only this case, the median and nearest-rank P90 are 10 calendar hours and the correction-cycle count is 1. Missing effort stays null; no staff/public effort is inferred from those 10 hours.

Each stage needs evidence/scenario text and a timezone-aware RFC3339 timestamp. Times must be nondecreasing, and edits use version checks so a stale browser cannot overwrite newer work. The exercise requires review then inspection before a fictional decision; this is a prototype rule, not a claim about an actual jurisdiction's process. A case may withdraw from any open stage. Terminal stages cannot be advanced. Quality reviews follow a fictional decision and are retained as versioned records.

## Measurement definitions

| Measure | Rule |
| --- | --- |
| Arrivals | Cases received on or before the selected cutoff, optionally limited to one exact category |
| Decision elapsed time | Calendar hours from receipt to the decision stage; corrections and pauses remain included |
| Median/P90 | Completed decision cases only; P90 is the nearest-rank order statistic |
| Open-case age | Calendar hours from receipt to cutoff for cases still open; reported separately as censored observations |
| Withdrawals | Counted separately and excluded from decision-time statistics |
| Stage time | Calendar hours in each recorded stage through cutoff; not active staff or public effort |
| Staff/public effort | Separately reported person-hours for each interval; a decision case enters an effort statistic only if every interval has that effort measurement |
| Quality | Most recent quality review recorded on or before the cutoff for a decided case; denominator and unreviewed decisions are explicit |
| Corrections | Number of entries into the awaiting-correction stage through cutoff |

All timestamps normalize to UTC. Future events relative to the cutoff are excluded, including quality reviews. An empty sample has a null statistic and sample size zero. Reporting multiple categories together may mix incomparable cases; use the category filter and confirm population rules. Historical cutoffs reflect the simulated event times, not when the operator typed the records. Reviewers and evidence are local user assertions, not authenticated independent findings. No statistical uncertainty estimate or causal attribution is provided.

## Persistence and interfaces

Cases, events and quality reviews are stored in the same SQLite workspace as the portfolio. Full JSON exports and SQLite backups include them. Use the [workspace backup instructions](APPLICATION.md#export-backup-and-restore).

- `GET /api/permits` lists fictional cases and the local mutation token.
- `POST /api/permits` creates a fictional case.
- `POST /api/permits/{id}/events` appends a permitted stage event with the expected case version.
- `POST /api/permits/{id}/quality` records a quality-review revision.
- `GET /api/permits/report?as_of=...&category=...` computes the report.

These routes share the application's loopback binding, host/origin checks and mutation token. They are for the local prototype, not an authenticated public API. There are no applicant identifiers, document uploads, external notifications, fee collection, approval integrations or live agency actions.

## Remaining acceptance work

Import and review the full project 009 source, identify the real permit type/program and accountable institution, confirm process rules and population boundaries, establish lawful data access, evaluate accessibility and recovery, and seek qualified review. The original synthetic Layer A packet remains blocked and unchanged. This prototype does not satisfy those missing requirements or mark project 009 complete.
