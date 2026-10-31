# Project 023 — Controllable justice caseflow, remedies and reentry

This extends the existing [justice observatory](JUSTICE-LAB.md) with an isolated **fictional process-control scenario** based on the [full specification supplied by the user](sources/023-user-specification.md). It records milestones and checks, not actual court acts. The observatory's evidence, pilots and metrics are not modified by simulation controls.

## Open and run

From layer-b, Python 3.12:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/scenarios?workflow=justice>, or use **Control caseflow and remedy scenarios** in the justice observatory. Select Project 023 and create SYN-JUSTICE-CONTROL with a fictional label/start time, actor and note.

Do not enter actual case numbers, party identities, sealed/juvenile/victim records, confidential communications or allegations about real people. No rulings, sentencing, bail, release, guilt, eligibility or individual risk judgments are performed. There is no production court connection or authenticated professional approval.

## All fifteen states

| State | Valid next states |
| --- | --- |
| ACCESS_REQUESTED | FILED, WITHDRAWN |
| FILED | NOTICE_RECORDED, WITHDRAWN |
| NOTICE_RECORDED | NOTICE_REVIEW, WITHDRAWN |
| NOTICE_REVIEW | HEARING_RECORDED after notice check, NOTICE_RECORDED, WITHDRAWN |
| HEARING_RECORDED | DECISION_RECORDED, NOTICE_RECORDED, WITHDRAWN |
| DECISION_RECORDED | REVIEW_REQUESTED, REMEDY_RECORDED, REENTRY_HANDOFF |
| REVIEW_REQUESTED | REMANDED, REMEDY_RECORDED, WITHDRAWN |
| REMANDED | NOTICE_RECORDED, WITHDRAWN |
| REMEDY_RECORDED | REMEDY_REVIEW, WITHDRAWN |
| REMEDY_REVIEW | CLOSED after remedy check, REMEDY_RECORDED, REVIEW_REQUESTED |
| REENTRY_HANDOFF | FOLLOW_UP_RECORDED, WITHDRAWN |
| FOLLOW_UP_RECORDED | CONTINUITY_REVIEW, REENTRY_HANDOFF, WITHDRAWN |
| CONTINUITY_REVIEW | CLOSED after reentry check, REENTRY_HANDOFF, WITHDRAWN |
| CLOSED, WITHDRAWN | None |

This is an editorial scenario graph, not a jurisdiction's procedural rules or a complete representation of all justice pathways. WITHDRAWN ends only this fictional scenario and does not vacate a real judgment. REENTRY_HANDOFF is a service-continuity record, not a custody/release determination.

All shared controls apply: pause/resume/stop, manual clock, valid steps, every-state presets, reset to ACCESS_REQUESTED, read-only snapshot inspection and append-only restoration.

## Three independent record-review gates

1. **Notice record check before hearing.** A current passing review at NOTICE_REVIEW must be recorded by an identifier distinct from both current filing and notice recorders. It does not certify legally sufficient notice or due process. A revised notice invalidates the previous check.
2. **Remedy record check before closure.** REMEDY_REVIEW requires a distinct identifier from the current decision and remedy recorders. Revision of the remedy invalidates the pass. The check does not verify that relief reached an affected person or that an order is lawful.
3. **Reentry continuity check before closure.** CONTINUITY_REVIEW requires a distinct identifier from current handoff and follow-up recorders. A new handoff/follow-up cycle invalidates the pass. No rehabilitation, recidivism, benefit or release outcome is assessed.

All identifiers and assertions are local, not authenticated reviewers or qualified officials. A pass for one phase cannot satisfy another phase or a revised path. Checks require RUNNING execution. Pause/stop blocks transitions/checks while explicit TICK can still advance fictional waiting.

## Reproduce both closure paths

1. Record FILED → NOTICE_RECORDED → NOTICE_REVIEW, with 60 fictional minutes per step.
2. Observe the hearing hold; record a passing check using a separate identifier.
3. Record HEARING_RECORDED → DECISION_RECORDED. This records a fictional milestone only; no decision content or outcome is produced.
4. Record REVIEW_REQUESTED → REMANDED → NOTICE_RECORDED → NOTICE_REVIEW. The old notice pass cannot advance the new hearing; record a new check.
5. Record another hearing/decision, then REMEDY_RECORDED → REMEDY_REVIEW. A current remedy check enables CLOSED.
6. Restore the earlier checked notice snapshot into a new event. Repeat hearing/decision, then REENTRY_HANDOFF → FOLLOW_UP_RECORDED → CONTINUITY_REVIEW. A distinct fresh continuity check enables the alternative CLOSED branch.
7. Try all fifteen presets and WITHDRAWN. Reload to verify persistence.

Presets use the shortest valid path, 60 minutes per edge, and insert an explicit fictional SYN-PRESET-CHECKER record before every gated transition. CLOSED defaults to the shorter remedy branch and requires PASS. To rehearse reentry closure, load CONTINUITY_REVIEW and then close after a pass. Restoring a snapshot reproduces the fictional branch and never restores real legal authority.

## Diagnostics and boundaries

- justice_review_pending marks current access/filing/notice/hearing/review/remand phases in this scenario; it is not a real docket or legal status.
- filing_to_latest_decision_minutes runs from first FILED to the latest DECISION_RECORDED on the current branch. While a review/remand/rehearing is pending, the old decision time is censored (null). WITHDRAWN has null decision timing. All past milestones remain in the path.
- remand_cycles counts REMANDED records; notice_revisions counts NOTICE_RECORDED records beyond the first. These counts are not judicial error or misconduct findings.
- completion_elapsed_minutes runs from ACCESS_REQUESTED to checked CLOSED, including preparation, waiting, remands and remedy/reentry steps. It does not prove lawful disposition, effective relief or rehabilitation. The two closure branches are labelled REMEDY_RECORD or REENTRY_RECORD.
- judicial_outcomes_assessed=false, remedy_effectiveness_verified=false, recidivism_assessed=false, execution_authorized=false and legal_review=REQUIRED remain explicit.
- No legal deadline calculation, school/court/institution rankings, causal effect, sentencing consistency score or predictive individual-risk model is implemented.
- This single synthetic run has no case-type/complexity population denominator; use the existing observatory's declared strata and measurement contracts for separately reviewed analysis.

Snapshot hashes, actor/reason, optimistic versions, transaction rollback, audit/export/backup and source snapshot restoration follow the [shared scenario controls](SCENARIO-CONTROLS.md). Stored histories remain separate from justice_pilots/evidence records. Local SQLite is editable and identifiers are asserted; this is not an authenticated justice information system.

## API, tests and handoff

POST /api/scenarios accepts workflow=justice. GET /api/scenarios publishes the graph and three phase gates. Existing commands/reports/export/backup apply.

    python -m unittest tests.test_justice_scenarios -v
    python -m civic_portfolio export --output justice-controls.json
    python -m civic_portfolio backup --output justice-controls-backup.sqlite3
    python -m civic_portfolio --db justice-controls-backup.sqlite3 serve --port 8766

Ten tests cover all states and preset checks, distinct notice/record reviewers, remand/rehearing censoring, revised remedies, both closure paths, reentry handoff revisions, pause/stop/withdrawal, exact restore, invalid commands, stale writes, backup/observatory isolation and nonjudicial API fields. Browser CI exercises notice holds, remand, both closure paths, restore, every preset, persistence and mobile layout alongside previous workflows.

Actual official data integration, applicable procedural rules, qualified legal/practitioner/security review, real remedies and the institutional 90-day pilot remain outstanding. This adds controllable software behavior and does not complete Project 023's real-world success criteria.
