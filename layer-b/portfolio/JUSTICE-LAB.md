# Project 023 — Courts, Justice & Corrections Observatory

An implemented **synthetic local software workspace**, based on the [full specification supplied by the user](sources/023-user-specification.md). [Provenance and SHA-256](sources/023-provenance.json) identify the Markdown transcription. This is not a fetched/authenticated copy of the linked Google Doc; source names, statistics and legal applicability were not independently verified. No institutional pilot has occurred and no real-world improvement is claimed.

## Run and use

From `layer-b`, Python 3.12:

```sh
python -m civic_portfolio serve --port 8765
```

Open <http://127.0.0.1:8765/justice>, or use the **Project 023 justice observatory** link on the portfolio home page. The app requires no runtime packages beyond the Python standard library.

1. Enter a local identifier. **Import supplied Project 023 specification** records its full text, origin and hash in the portfolio's source catalog as an unreviewed version. Read/review it in the portfolio workspace separately. Importing again creates another version and clears prior project scope/work assertions.
2. Register `SYN-JUSTICE`, a fictional jurisdiction, process owner, data steward, authority reference, privacy/retention rules and challenge route at `2026-01-01T00:00:00Z`.
3. Append EVIDENCE `SYN-NOTICE`, fictional text, origin and limitations, level C at `2026-01-01T01:00:00Z`. A requires an asserted official/independent verification reference; B needs two distinct source references. The software checks fields, not source truth or independence.
4. Append GAP `SYN-NOTICE-GAP`, dimension INFORMATION, module ACCESS, an understandable-notice question, owner, authority, review route, alternative explanation and selected evidence revision. The report shows all ten dimensions, including empty ones, and all eight module counts.
5. Register CASE `SYN-PATH`, declared case type, complexity and urgency, initial ACCESS. Record FILED at 02:00, FIRST_ACTION at 03:00 and RESOLVED at 04:00. Each transition requires owner, authority, review route, cause/classification and evidence. For each hour interval, declare waiting `30` and active `10` minutes; the remaining `20` stays unclassified. Blank waiting/active means unknown. Both must be blank or both measured. FIRST_ACTION can repeat for continuances; RESOLVED → FIRST_ACTION records remand without erasing history. CUSTODY or RELEASE can start a corrections/reentry-only pathway.
6. Append REMEDY `SYN-REMEDY`, linked gap, owner, OPEN and explanation. Append REMEDY STATUS → IMPLEMENTED. Use a different identifier and REMEDY CHECK against that implementation sequence. Only a passing latest check with current evidence permits CLOSED. A new implementation invalidates the earlier check even at an identical timestamp. CLOSED → REOPENED preserves age from original OPEN.
7. Register a METRIC contract: module, definition, unit, COUNT/RATIO, numerator and denominator definitions, period, owner, exclusions, uncertainty, subgroup limits, correction process, counter-metric and source evidence. Append an OBSERVATION. For RATIO, `2 / 4` displays `0.5`; denominator zero is rejected. A missing numerator requires null denominator and a missing-data reason. Further observations correct prior observations without deletion.
8. Add REVIEW notes for legal-source, statistical, operations, economic, rehabilitation, risk/rights and human-review roles, pinning the displayed latest analysis sequence. These are human-authored research-role notes, not autonomous model runs. Record disagreement and limitations. Further analysis/evidence/phase edits make earlier reviews stale. No set of reviews establishes legal approval.
9. Record PHASE findings/limitations for baseline (1–30), diagnosis (31–60) or controlled test (61–90). These are scenario records, not evidence that a real 90-day pilot occurred. Refresh the historical cutoff, reload to check persistence and export/backup from the portfolio.

## Specification traceability

| Supplied section | Implemented software | Remaining institutional/research work |
| --- | --- | --- |
| 1–2 Mission and topology | Bounded pilot context, owner/steward/authority/challenge route; access → filing → first action → resolution → remedy/custody/release → supervision/reintegration; repeated events/remands retained | Select and validate an actual process map, authority, community needs and accountable institution |
| 3 Ten-dimensional matrix | All ten diagnostic dimensions with evidence-pinned questions, module, owner, authority, review route and alternative explanation; empty dimensions visible | Practitioner validation; no automatic institutional findings |
| 4 Eight modules | ACCESS, CASEFLOW, FAIRNESS, CONDITIONS, REHABILITATION, REENTRY, REMEDIES, FINANCE classifications across gap/metric records | Module-specific real datasets, legal analysis, sentencing comparisons and credible outcome evaluations |
| 5 Balanced scorecard | Full metric contracts; count/ratio observations, missingness, revisions, subgroup limits and counter-metrics; separate A/B/C evidence inventories | Validate actual numerator/denominator definitions, case-mix adjustment, sampling and independent source verification; no automatic clearance/recidivism/cost calculations |
| 6 DTI | Strata by declared type/complexity/urgency; median/p90 elapsed resolution and unresolved age; transition elapsed/wait/active/unclassified minutes and cause assertions | Determine necessary versus avoidable delay with qualified reviewers; staffing/capacity collection remains a metric-contract exercise, not a validated DTI formula |
| 7 HedgeOps | Six research-role notes plus human review, explicit disagreements/limits, exact analysis/evidence pins and stale-review diagnostics | Actual specialist analysis, authenticated reviewers and human arbitration; no agents or consequential decision engine run automatically |
| 8 Safeguards | Synthetic IDs, no identity-specific fields, local-only service, token/origin controls, append-only API history, hashes, stale dependencies, challenge route and fixed legal/execution holds | Production identity/access/retention/security governance, actual chain of custody, qualified rights review; free text cannot automatically prevent sensitive content entry |
| 9 Pilot | Three phase evidence records and owners/limitations | The real 90-day California process, baseline, community consultation, controlled intervention and independent evaluation |
| 10 Sources | Supplied source descriptions retained in full source transcript; explicit source-origin and evidence records | Verify and license official datasets; no live connectors/imports supplied |
| 11 Success | Exportable methods, limitations, caseflow, gap, remedy, review and phase histories | Demonstrate actual improvements and unintended effects with reproducible institutional evidence |

## Measurement contract

Reports use UTC RFC3339 record timestamps and an inclusive historical cutoff. They describe recorded scenario time, not ingestion time; records may not precede the latest pilot activity. Optimistic versions reject stale concurrent writes (409). References are scoped to a pilot.

- **Evidence**: exact UTF-8 text SHA-256, original origin, limitations, separately asserted A/B/C label, immutable numbered revisions. Pins identify ID + revision. New revisions mark dependent records stale; they do not overwrite history. A current reference is not proof of truth. Full source/evidence text is included in export.
- **Caseflow**: group by declared case type, complexity and urgency. Filing-to-latest-resolution hours includes currently post-decision pathways with a recorded filing and resolution; a remand removes that pathway from this resolved sample until resolved again. Pending age starts at initial ACCESS registration, including pre-filing access time; it does not reset on remand. Reentry-only pathways have no adjudication duration. Samples explicitly report size, median and nearest-rank p90; empty samples have null statistics. No system-wide clearance rate or statutory deadline is inferred.
- **DTI intervals**: retain every transition, including repeated same-stage events. Supplied waiting + active minutes cannot exceed the interval. Unknown components remain null. Classification (avoidable assertion, necessary safeguard, complexity, party, unknown) is an assertion, not a legal or causal finding. No invented DTI composite formula.
- **Remedies**: current status and original open age for unresolved/reopened remedies. A passing check is tied to the exact implementation sequence and a distinct local recorder ID. Evidence revisions prevent stale implementation/check closure; a previously closed remedy remains historically closed with a stale-evidence warning until explicitly reopened. Software cannot verify delivery to a real person.
- **Metrics**: latest observation by event sequence supersedes previous values within its immutable contract. Use a new metric ID for changed definition/period/basis. COUNT has null denominator; RATIO has positive integer denominator. Integers are bounded to 10^9; ratios may exceed one (for example a clearance ratio). No weighting, institutional rankings, predictive scores or causal attribution. Stale source/observation evidence remains visible. Correction notes reside in the selected revised evidence content.
- **Review/phase**: notes retain asserted actor and pins. Review freshness requires the exact latest non-review event sequence and current evidence, allowing multiple roles to review the same analysis. A phase record proves only that a note was entered. All execution/legal/institutional acceptance fields remain fixed to false/required/not established.

## API, verification and handoff

| Method and path | Purpose |
| --- | --- |
| GET `/api/justice` | Pilots, schemas, dimensions, modules, roles and mutation token |
| GET `/api/justice/specification` | Bundled user specification, origin and hash |
| POST `/api/justice/import-specification` | Explicit source-catalog import, actor required; never auto-review |
| POST `/api/justice/pilots` | Register synthetic pilot context |
| POST `/api/justice/{id}/records` | Append typed record with version, kind, timestamp, actor and data |
| GET `/api/justice/{id}/report?as_of=2026-01-02T00:00:00Z` | Historical diagnostic report |

```sh
python -m unittest tests.test_justice -v
python -m unittest discover -s tests -v
python -m civic_portfolio export --output justice-workspace.json
python -m civic_portfolio backup --output justice-backup.sqlite3
python -m civic_portfolio --db justice-backup.sqlite3 serve --port 8766
```

The shared browser smoke tests use a disposable synthetic database. Export includes `synthetic_justice` pilot/event bodies plus the shared source and audit history. SQLite backup/restore is tested. Stop the app and retain an untouched backup before upgrades; restore a copy of the backup with the previous application version to roll back. API history is append-only but the local database itself is editable, not tamper-proof.

The app is loopback-only and single-workspace, with unauthenticated asserted identifiers. Do not expose it to the internet or enter real justice records. Retention is locally controlled: stop the app and delete the disposable database and exports when no longer needed; no automatic retention schedule is claimed. The original Layer A packet remains blocked. This software does not implement a production court/corrections system or complete the institutional success criteria.
