# Project 015 — synthetic utilities continuity

## Delivered scope

The local application tracks fictional utility assets, interruptions, affected-connection assertions, work-order reference labels, restoration records, scenario-quality evidence checks, closure and reopening. Reports separate checked restoration-cycle durations, verification delay, unresolved ages, repeat interruptions, unknown connection counts and escalation-reference gaps. It follows the [editorial plan](plans/015.md), not the unread linked source. No actual utility controls, work orders, dispatch, escalation messages or safety certification are performed.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/utilities>. Restart an existing server to add the routes/tables. Existing workspace records remain intact; no incidents, checks or measurements are inserted automatically.

## Fictional walkthrough

1. Enter an operator identifier. Register `SYN-UTILITY-001`, category WATER, area `Demo area`, aggregate connections 20, registered `2026-01-01T00:00:00Z`, with fictional evidence. Leave the connection capacity blank when unknown.
2. Report `SYN-OUTAGE-001`, declared start `01:00:00Z`, report `02:00:00Z`, initially affected connections 10, scenario severity SAFETY_REVIEW, and evidence. The initial count is explicitly asserted from the declared start; this is not an independent observation or customer register. Leave the escalation reference blank to preserve that evidence gap.
3. Record ASSESSED at `03:00:00Z`, current affected connections 8, with a fictional responsible-process/escalation-route label. This records a reference and sends no message.
4. Record WORK_IN_PROGRESS at `04:00:00Z`, affected connections 8, and a fictional work-order reference label. It neither creates nor dispatches a work order in this or another system.
5. Record RESTORATION_RECORDED at `06:00:00Z` with explicit zero affected connections. This is a recorded service-count assertion, not checked restoration or a statement that actual water/service is safe. Closure is rejected without a qualifying current-record check.
6. Record a quality-evidence check at `07:00:00Z`, result Pass, quality UNKNOWN, with a fictional criteria reference and distinct verifier identifier. Closure remains blocked. A passing check of an unknown-quality observation does not establish that the declared scenario criteria are met.
7. Record a new check at `07:30:00Z`, result Pass and MEETS_SCENARIO, with criteria/evidence. Close at `08:00:00Z`, again using explicit zero affected connections. At cutoff `12:00:00Z`, the completed cycle is five hours from declared start to restoration record; verification lag is 1.5 hours. Neither duration includes a claim of actual restoration or safety.
8. Reopen at `10:00:00Z`, affected connections 5, with evidence. At noon, current-cycle age is two hours, original-incident unresolved age is eleven hours, and the earlier checked five-hour completed cycle remains in history. A later restoration requires its own check, even if simulated timestamps tie.

Use full RFC3339 UTC/offset timestamps for all examples, on `2026-01-01`. Counts are explicit nonnegative integers, bounded by known asset capacity; unknown counts remain null. Interruption start must be no later than report and no earlier than asset registration in this prototype. Stage/check times are nondecreasing, and expected versions reject stale writes.

## Proposed workflow and checks

REPORTED → ASSESSED → WORK_IN_PROGRESS → RESTORATION_RECORDED → CLOSED. Assessment and work stages may repeat to update evidence/counts. A restoration may return to work, and a closed incident may reopen into a fresh assessment/work/restoration cycle. Closure requires the latest check for the **exact current restoration event** to pass and assert MEETS_SCENARIO with a declared fictional criteria reference. UNKNOWN, DOES_NOT_MEET, failed or stale checks cannot close the incident. A distinct verifier identifier is required; identities, criteria and results remain local user assertions, not authenticated professional review or real safety findings.

Escalation-route references can be recorded at intake or assessment. The report shows SAFETY_REVIEW scenarios without a reference, including historical gaps at earlier cutoffs. A reference's presence does not mean that escalation occurred or that a real protocol was followed. Quality does not follow automatically from service-count restoration, and a completed cycle does not erase earlier unknown/failed quality records.

## Measurement contract

| Measure | Definition and boundary |
| --- | --- |
| Checked restoration-cycle hours | Initial interruption start, or explicit reopening, to the associated restoration record for a cycle that has a passing MEETS_SCENARIO check and closure visible at cutoff |
| Verification lag | Restoration-record timestamp to its latest qualifying check before closure; separate from service-count duration |
| Open-cycle age | Current cycle start to cutoff for incidents not closed; separately censored |
| Original-incident age | Original declared start to cutoff for still-open incidents; reopening never erases this context |
| Reopen events | Recorded reopens, not a unique asset/customer repeat-failure rate |
| Unclosed restoration records | Incidents currently at RESTORATION_RECORDED, even when affected count is asserted zero |
| Failed/unknown quality records | Checks that fail or do not assert MEETS_SCENARIO, including observations later corrected |
| Incident-associated connection-hours | Piecewise asserted affected counts × calendar hours for each incident, summed through cutoff; initial count applies from declared start |
| Unknown intervals | Positive-duration intervals with unknown affected counts; any such interval makes the complete burden total null. The known-interval subtotal is separate |

For the walkthrough, before reopening the reported burden is `(10 × 2) + (8 × 1) + (8 × 2) = 44` incident-associated connection-hours; recorded restored/closed intervals contribute zero. Reopening adds `5 × 2 = 10`, giving 54 by noon. If another incident has an unknown count for a positive-duration interval, the complete total becomes null while the known subtotal remains 54. Unknown intervals are never silently treated as zero.

Concurrent incidents may involve the same connections and are **not deduplicated**. These are incident-associated counts, not unique households/customers, SAIDI, SAIFI or network availability. Reported zero service-count impact does not imply acceptable water or service quality. An asset with no recorded incident does not establish reliable service. Area and utility filters use exact matches; all dates normalize to UTC. Incidents not yet reported at cutoff are excluded even if their later declared start precedes cutoff. Empty duration samples remain null with explicit counts; P90 uses nearest rank. No real-world causal, reliability or safety estimate is inferred.

## Privacy and operating boundary

Use invented `SYN-` identifiers, aggregate connection counts and fictional reference labels. There are no customer names, addresses, accounts, critical-infrastructure control fields or real laboratory measurements in the structured model. Free text is not a redaction system. WATER/SEWER/POWER/OTHER are scenario labels. No actual water-quality threshold, restoration authorization, service control, repair dispatch, public warning or escalation message is supplied or performed.

## Interfaces and persistence

- `GET /api/utilities` returns fictional assets and incidents.
- `POST /api/utilities/assets` registers an asset.
- `POST /api/utilities/incidents` reports an interruption.
- `POST /api/utilities/incidents/{id}/events` records a permitted stage/count update or reopening.
- `POST /api/utilities/incidents/{id}/checks` checks the current restoration's declared scenario-quality evidence.
- `GET /api/utilities/report?as_of=...&area=...&utility=...` computes historical measures.

Routes share the loopback-only server, host/origin checks and local mutation token. Full JSON export and SQLite backup preserve asset, event, check and audit histories. See [backup/restore](APPLICATION.md#export-backup-and-restore).

## Outstanding acceptance

Import and review the full source; confirm actual asset scope, interruption boundaries, authorized data access, outage/overlap definitions, responsible escalation processes, safety/quality criteria, continuity safeguards and accessible reporting. Qualified acceptance and separate institutional authorization remain necessary. This prototype does not mark project 015 complete or change the original Layer A hold and pinned packet.
