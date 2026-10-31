# Project 010 — synthetic asset maintenance

## Delivered behavior

The local application provides a fictional asset register, condition reports, work-order stages, explicit triage rationale, scheduling/team records, repair-verification checks, reopening and historical queue reports. This prototype follows the [proposed project plan](plans/010.md) and [B6 public-works prompts](../docs/domains/B6-public-works-and-essential-services.md). It is not derived from the unread linked Google Doc and does not implement an actual jurisdiction's maintenance rules.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/maintenance>. Restart an existing server to load the new routes and tables. Existing project, source and permit records remain in the workspace. No fictional assets or measurements are inserted automatically.

## Fictional walkthrough

1. Enter an operator identifier. Register asset `SYN-ASSET-001`, category `Fictional sidewalk`, area `Demo area A`, at `2026-01-01T00:00:00Z` with scenario evidence.
2. Create work order `SYN-WORK-001` for that asset at `2026-01-01T01:00:00Z`, describing a fictional condition and its evidence.
3. Record `TRIAGED` at `02:00:00Z` on the same date, choose a priority and document the rationale. The options are ROUTINE, URGENT and SAFETY_REVIEW; none dispatches work or establishes an actual safety assessment.
4. Record `SCHEDULED` at `03:00:00Z`, naming a fictional team, then `IN_PROGRESS` at `04:00:00Z`, then `VERIFICATION` at `05:00:00Z`.
5. Attempting `CLOSED` without a passing check is rejected. Record a check at `06:00:00Z` with criteria, evidence and a distinct verifier identifier, then close at `07:00:00Z`. These identifiers and checks are local assertions, not authenticated independent inspections.
6. Set report cutoff `2026-01-02T00:00:00Z`. With this single closed order, verified elapsed time is six calendar hours from the original report; it is not active repair effort.
7. Reopen by recording `TRIAGED` at `09:00:00Z` with fresh rationale and priority. The report now shows one reopen event and one open order. A second repair must pass a new verification check before closing again.

Use full RFC3339 timestamps with a UTC `Z` or numeric offset. Stage and check times must be nondecreasing. Every work order and asset has an explicit fictional ID starting `SYN-`. A work order must refer to a registered asset and cannot predate its registration. Stage writes require the expected version and evidence; stale edits are rejected.

## Verification and corrections

The stage sequence is REPORTED → TRIAGED → SCHEDULED → IN_PROGRESS → VERIFICATION → CLOSED. Failed checks can return the order from VERIFICATION to IN_PROGRESS. Closed orders can reopen to TRIAGED. Closure requires the most recent check to pass and be attached to the exact current verification-stage event. Old checks cannot satisfy a new repair cycle, even if the simulated timestamps are identical. A distinct verifier identifier is required from the latest work actor; this is a record-separation rule, not proof of independent identity.

## Measures

| Measure | Definition and limitation |
| --- | --- |
| Assets | Fictional assets registered by the cutoff, optionally filtered to one exact area |
| Open backlog | Orders whose last stage at the cutoff is not CLOSED |
| Backlog age | Calendar hours from original report to cutoff; open orders are censored and excluded from closure-time statistics |
| Verified elapsed time | Original report to latest closure, for orders closed at the cutoff; includes waiting, correction and reopened periods |
| Median/P90 | Null for no observations; P90 uses nearest rank |
| Priority queue | Latest recorded priority at the cutoff for open orders; UNTRIAGED is retained explicitly |
| Reopen events | Transitions out of CLOSED, a rework signal rather than a verified repeat-defect rate |
| Failed verifications | Recorded failed checks by cutoff, including failures subsequently corrected |
| Area inventory | Asset, reported-order and open-order counts per fictional area; includes registered areas without work orders |

All times normalize to UTC. Future events/checks relative to cutoff are excluded. Area inventory is context, not population coverage, service equity or proof of adequate access. No staff effort, repair cost, causal effect or real-world performance is inferred.

## Interfaces and persistence

- `GET /api/maintenance` returns fictional assets and orders.
- `POST /api/maintenance/assets` registers a fictional asset.
- `POST /api/maintenance/orders` creates a condition/work-order record.
- `POST /api/maintenance/orders/{id}/events` appends an allowed stage with expected version.
- `POST /api/maintenance/orders/{id}/checks` records verification for the current stage.
- `GET /api/maintenance/report?as_of=...&area=...` computes historical measures.

These routes share the local app's host/origin protections, mutation token and loopback-only binding. Full JSON exports and SQLite backups include maintenance records and the audit history. See [backup and restoration](APPLICATION.md#export-backup-and-restore). No deletion or silent history rewriting is provided by this prototype.

## Outstanding acceptance

Import the full project source and confirm requirements, accountable owners, safety/escalation rules, accessible reporting routes, actual prioritization and lawful records access. Qualified review and separate institutional decisions remain necessary before any real operation. No actual inspection, repair dispatch, purchase, procurement award or safety certification is performed. The original Layer A hold and synthetic permit packet remain unchanged.
