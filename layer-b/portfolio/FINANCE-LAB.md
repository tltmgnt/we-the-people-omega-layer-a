# Project 018 — Synthetic finance reconciliation lab

This local prototype implements the proposed bounded category-reconciliation exercise. The linked project source is unread. Actual accounting rules, requirements, reviewer acceptance and institutional adoption remain outstanding. The project remains incomplete.

Run from `layer-b`:

```sh
python -m civic_portfolio serve --port 8765
```

Open <http://127.0.0.1:8765/finance>. Enter fictional records only; no personal information, account numbers, credentials or real financial documents.

## Reproducible exercise

1. Create `SYN-BUDGET`, currency label `USD`, minor-unit digits `2`, period `Fictional FY2026`, basis `Scenario accrual`, timestamp `2026-01-01T00:00:00Z`, actor `RECORDER`.
2. Append an EXPENDITURE ENTRY of `101` at `2026-01-01T01:00:00Z`, with a fictional evidence reference and explanation. The recorded amount is 101 minor units (1.01 declared currency units), not 101 currency units.
3. Switch actor to `CHECKER`; append a RECONCILIATION comparison of `100` for EXPENDITURE. Report discrepancy is `1` minor unit.
4. Switch back to `RECORDER`; append a signed adjustment ENTRY of `-1`, retaining the original record and explaining the correction. The earlier comparison becomes stale, even with identical timestamps.
5. Switch to `CHECKER` and append another comparison of `100`. The current discrepancy is zero. This records agreement with a supplied fictional total, not an audit opinion or independent source authentication.
6. Append an OUTCOME note describing a fictional service observation and its limitations. Category/amount are absent from this record; payment does not establish delivery or public benefit.
7. Reload, select the ledger and check history. Export the workspace or use the application's documented SQLite backup command; restore by serving a copy of that backup as documented in [APPLICATION.md](APPLICATION.md).

## Input and measurement contract

| Item | Meaning and boundary |
| --- | --- |
| Context | Immutable declared currency label, minor-unit digits (0–4), reporting-period label and accounting-basis label. They are assertions, not jurisdictional accounting validation. Create separate ledgers for different contexts; no cross-ledger totals. |
| Categories | APPROPRIATION, ALLOCATION, OBLIGATION, EXPENDITURE, OUTLAY remain separate. No combined spending total or assumed chain inequalities. No automatic transaction matching or authority validation. |
| Amount | JSON integer minor units; booleans, strings and floats rejected. Each entry/comparison and running category total is bounded to ±10^12. Signed corrections require a note/reference and append history. |
| Recorded total | Signed sum of the selected category's entries recorded by cutoff. No entries means null, rather than zero. |
| Comparison | Latest supplied category comparison total and evidence reference by cutoff. Current only when pinned to the latest exact entry sequence. Recorder/reconciler identifiers must differ for every entry in that category; identifiers are unauthenticated local assertions. |
| Discrepancy | Recorded minus comparison, only with entries and a current comparison; otherwise null. A discrepancy prompts investigation and is not proof of misconduct. The explanation is recorded in each comparison note. |
| Unresolved age | Hours from first category entry to cutoff for categories missing a current comparison or with nonzero discrepancy. Median/p90 nearest rank and category sample size; empty sample yields null. This is not audit-finding age. |
| Outcomes | Separate evidence-linked, unverified notes; no cost-per-service ratio or causal attribution inferred. |
| Time | Required timezone-aware RFC3339, UTC normalized; nondecreasing record times, optimistic versions, historical cutoff. Reporting period is a declared label, not an enforced fiscal calendar. |

All writes are transactional, append-only through the API, audited and protected by the shared local mutation token. Concurrent stale saves return 409. Original entries are never overwritten by adjustments. SQLite files are locally editable; this is not a tamper-proof accounting system.

## API and tests

- `GET /api/finance`: ledger histories and local mutation token.
- `POST /api/finance/ledgers`: create a fictional context.
- `POST /api/finance/{id}/records`: append ENTRY, RECONCILIATION or OUTCOME with current version.
- `GET /api/finance/{id}/report?as_of=2026-01-02T00:00:00Z`: category report and separate outcome notes.
- Workspace export includes raw `synthetic_finance` ledgers/event JSON; SQLite backup preserves all history.

```sh
python -m unittest tests.test_finance -v
```

The browser smoke exercises discrepancy correction, stale comparisons, outcome separation, reload persistence and mobile layout. No live payments, tax calculations, grants, purchasing, budget decisions or authoritative ledger replacement occur. Actual source import, qualified accounting/legal review and real operating acceptance are still required.
