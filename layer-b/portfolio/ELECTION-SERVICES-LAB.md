# Project 017 — synthetic election-service administration

## Delivered scope

The local application records fictional administrative service sessions, scenario-readiness assertions, revision-specific checks, anonymous access observations and correction/closure/reopening histories. It follows the [editorial plan](plans/017.md), not the unread linked source. It is a bounded nonpartisan service-evidence prototype; formal representation analysis and actual election operations are not implemented.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/election-services>. Restart an existing server to add the routes/tables. Existing workspace records remain intact. Every new session starts with five UNKNOWN scenario-readiness items; no readiness finding, observation or correction is inserted automatically.

## Fictional walkthrough

1. Enter an operator identifier. Register `SYN-SERVICE-001`, label `Fictional administrative information service`, area `Demo area`, channel IN_PERSON, registered `2026-01-01T00:00:00Z`, open `08:00:00Z`, close `18:00:00Z`. These are invented scenario hours, not actual voting hours or official service information. A fictional public-report reference label is optional; missing references remain explicit.
2. At `01:00:00Z`, record ACCESSIBLE_CHANNEL as GAP against a fictional criterion, with evidence. Check that exact item revision at `02:00:00Z` using a distinct identifier. The report now counts one checked scenario gap, not a legal or election-validity finding.
3. At `03:00:00Z`, record a MET revision for the same item with new evidence. The old check cannot verify it. A fresh check at `04:00:00Z` counts one checked MET item; the other four items remain unknown. Even all five checked MET assertions would not establish institutional acceptance or actual readiness.
4. At `05:00:00Z`, record `SYN-ACCESS-001`, barrier PHYSICAL_ACCESS, a fictional non-identifying observation, and optional aggregate affected-service observations 2. Observations may describe planning gaps before a session opens; they are not assertions that actual people were denied service.
5. At `06:00:00Z`, record CORRECTION_RECORDED with a fictional correction reference and evidence. Attempted closure at `07:00:00Z` is rejected without a passing check for this exact correction. Check at `07:00:00Z`, then close at `08:00:00Z`.
6. At cutoff `12:00:00Z`, recorded correction time is one hour from observation to correction record, and verification lag is one hour. These are local evidence measures, not proof that actual access was restored.
7. Reopen at `09:00:00Z` with repeated-observation evidence. At noon, unresolved age is seven hours from original observation; the observation leaves the current closed sample. A new correction needs a new check, even if simulated timestamps tie.
8. At `10:00:00Z`, add another fictional observation, category COMMUNICATION, with unknown affected count. The report retains that count as null and keeps both observations separate; no unique voter count or access-disparity rate is inferred.

All example times are on `2026-01-01` and must be entered as full RFC3339 UTC/offset timestamps. Session activity is nondecreasing across readiness, observations, corrections and checks. Expected session versions reject stale edits. Opening must follow registration or coincide with it; closing must be later than opening. The prototype does not check any actual election calendar or service requirement.

## Proposed evidence workflow

The five scenario-readiness items are ACCESSIBLE_CHANNEL, STAFFING_PLAN, PUBLIC_INFORMATION, CONTINUITY_PLAN and CORRECTION_ROUTE. UNKNOWN, MET and GAP are assertions against declared fictional criteria. MET/GAP requires a criteria reference; each new assertion invalidates earlier checks for that item. Checks require a distinct identifier from the recorder, but identities/results remain local assertions, not authenticated independent review or official certification.

Access observations start OPEN. They can move to CORRECTION_RECORDED, then CLOSED only with a passing check bound to the exact current correction record. A correction may be revised, and a closed observation may be REOPENED. Previous correction checks cannot close a revised or reopened cycle. A failed check leaves the observation unresolved. Closure records the prototype's evidence workflow, not a legal remedy, verified voting access or election-integrity conclusion.

## Measures and limits

| Measure | Definition and boundary |
| --- | --- |
| Checked MET/GAP items | Latest scenario assertion per item with a passing revision-specific check; UNKNOWN/unchecked/failed items remain separate |
| Public-report references | Missing fictional reference labels are counted; a label does not authenticate a report or its applicability |
| Access observations | Recorded non-identifying observations by generic service barrier; duplicates/overlap may exist |
| Checked correction time | Original observation to latest correction record for observations currently closed with qualifying checks; not time of an actual service action |
| Check lag | Correction-record time to latest qualifying check before closure |
| Unresolved age | Original observation to cutoff for open/correction-recorded/reopened observations; separately censored and never reset on reopening |
| Reopen events | Recorded reopens, not unique people or a verified recurring-rights violation rate |
| Aggregate affected observations | Optional explicit counts, not unique voters, denied ballots or eligible-person counts; unknown totals remain null |
| Area inventory | Registered-session, observation and unresolved counts, including areas with sessions but zero observations; no population denominator or access-equity conclusion |

Historical cutoffs select visible readiness revisions, checks and access histories first. Area and channel filters use exact fictional labels. Sessions may be assessed before opening; no service availability or actual operating hours are inferred. Closed-sample statistics exclude observations later reopened at the selected cutoff, while full history remains intact. Medians and nearest-rank P90 are descriptive synthetic statistics with explicit counts; empty samples remain null. Zero complaints never establish adequate access or absence of reporting barriers.

Every report explicitly retains `institutional_acceptance: NOT_ESTABLISHED`, `election_validity_assessed: false`, `representation_assessed: false` and `execution_authorized: false`. No number of checks or closed observations changes those boundaries.

## Privacy, neutrality and operating boundary

Use invented IDs, locations and non-identifying scenario text only. The structured model contains no voter identities, contact data, registration/eligibility records, political affiliations/preferences, ballot contents, vote tallies or election results. Free text is not a redaction system. No individual-level profiling, voter targeting, turnout inference, persuasion, eligibility decision, election-validity/fraud judgment, actual service change or outreach occurs. Barrier categories describe generic administrative access, not political or demographic segments.

## Interfaces and persistence

- `GET /api/election-services` returns fictional sessions and histories.
- `POST /api/election-services/sessions` registers a session.
- `POST /api/election-services/sessions/{id}/readiness` records a scenario assertion.
- `POST /api/election-services/sessions/{id}/readiness-checks` checks the current item revision.
- `POST /api/election-services/sessions/{id}/observations` records an anonymous access observation.
- `POST /api/election-services/sessions/{id}/observations/{observation_id}/events` records correction, closure or reopening.
- `POST /api/election-services/sessions/{id}/observations/{observation_id}/checks` checks the current correction record.
- `GET /api/election-services/report?as_of=...&area=...&channel=...` computes evidence diagnostics.

Routes share the loopback-only server, host/origin checks and local mutation token. Full workspace JSON export and SQLite backup preserve session/assertion/check/observation histories and audit entries. See [backup/restore](APPLICATION.md#export-backup-and-restore).

## Outstanding acceptance

Import and review the full project source; establish actual administrative scope, public information sources, lawful evidence handling, applicable service/access requirements, qualified verification and accountable correction routes. Representation-related requirements remain unimplemented pending source and scope confirmation. Qualified acceptance and separate institutional authorization remain necessary. This prototype does not mark project 017 complete or change the original Layer A hold and pinned packet.
