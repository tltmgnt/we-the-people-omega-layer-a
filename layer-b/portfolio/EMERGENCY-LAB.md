# Project 022 — Controllable emergency-readiness exercise

A bounded **fictional rehearsal**, based on the registered title and editorial plan. The full linked source remains unread. This prototype records exercise milestones and one bounded after-action/correction pathway. It does not dispatch, alert, route emergency resources, operate safety-critical systems or certify readiness.

## Open and run

From layer-b, Python 3.12:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/scenarios?workflow=emergency>, or choose **Project 022 · Emergency-readiness exercise**. Create SYN-EXERCISE with a fictional label, start time, actor and note.

Do not enter actual emergency requests, responder names/locations, operational deployment plans, sensitive infrastructure details, credentials or real incident information. All records and checks are unauthenticated local assertions in a loopback-only single-workspace sandbox.

## All eleven states

| State | Valid next states |
| --- | --- |
| DESIGNED | READINESS_RECORDED, CANCELLED |
| READINESS_RECORDED | READINESS_REVIEW, CANCELLED |
| READINESS_REVIEW | EXERCISE_STARTED after current readiness pass, READINESS_RECORDED, CANCELLED |
| EXERCISE_STARTED | RESPONSE_RECORDED, ABORTED |
| RESPONSE_RECORDED | AFTER_ACTION_RECORDED, ABORTED |
| AFTER_ACTION_RECORDED | CORRECTION_RECORDED, CANCELLED |
| CORRECTION_RECORDED | CORRECTION_REVIEW, CANCELLED |
| CORRECTION_REVIEW | CLOSED after current correction pass, CORRECTION_RECORDED, CANCELLED |
| CLOSED, CANCELLED, ABORTED | None |

Every state has the shared applicable pause/resume/stop, manual clock, step, preset, reset, snapshot inspection and append-only restore controls. Reset returns this workflow to DESIGNED. Cancelled and aborted scenarios are terminal, not completed improvements.

This graph is an editorial demonstration, not a prescribed emergency management procedure. The readiness and correction checks validate recorded scenario assertions only. There are no automatic legal/operational approvals, staffing adequacy rules or response-time standards.

## Two separate checks

### Readiness before simulated start

Record READINESS_RECORDED → READINESS_REVIEW. The next EXERCISE_STARTED transition is unavailable until a current passing REVIEW. The checker identifier must differ from the current readiness recorder. A failure holds the transition.

READINESS_REVIEW → READINESS_RECORDED → READINESS_REVIEW creates another revision; the earlier pass no longer satisfies the gate. Explicit manual clock advancement does not expire the check because this demonstration has no validated time-to-expiry rule. Real readiness remains uncertified regardless.

### Corrective action before simulated closure

After a checked start, record RESPONSE_RECORDED → AFTER_ACTION_RECORDED → CORRECTION_RECORDED → CORRECTION_REVIEW. Readiness approval cannot close the corrective pathway: the current correction revision requires its own pass.

The correction checker must differ from **both** current after-action and correction recorders. Returning to CORRECTION_RECORDED invalidates the earlier correction pass. A current passing correction check enables CLOSED.

The after-action/correction record is a milestone and attributable evidence note for one bounded finding, not a full incident inventory or validated multi-finding closure register. A real exercise program requires qualified design and independent acceptance.

## Reproducible walkthrough

1. Create the run at 2026-01-01T00:00:00Z.
2. Advance to readiness review, 60 fictional minutes per edge. Try starting before a check; the control remains unavailable.
3. Use a distinct checker, record failure then pass. Revise readiness to observe the old pass becoming stale, or proceed to EXERCISE_STARTED.
4. Record RESPONSE_RECORDED after 15 minutes, then after-action/correction/review milestones at 60 minutes each.
5. Attempt closure before a correction pass, or use an identifier matching either recorder; both are held. Record a distinct passing check.
6. Revise the correction and record a fresh check, then close. The diagnostic response interval remains 15 fictional minutes and is not an operational performance conclusion.
7. Restore the earlier checked readiness snapshot into a new history event. This restores the fictional state and check together; it does not create operational authority.
8. Try every preset, including CANCELLED and ABORTED. Reload to verify persistence.

Checks require RUNNING execution. PAUSE/STOP prevents transitions/checks; manual TICK still advances fictional elapsed time. There is no background timer or live processing.

## Presets explicitly replay gates

Presets replay a shortest valid path at 60 minutes per edge. Before every gated phase they insert a visible fictional SYN-PRESET-CHECKER record, distinct from SYN-PRESET-RECORDER. An EXERCISE_STARTED preset includes a readiness pass; a CLOSED preset includes **both** readiness and correction passes.

Current quality resets on ordinary phase transitions, while prior review records remain visible. READINESS_REVIEW and CORRECTION_REVIEW can be loaded as UNREVIEWED, PASS or FAIL. CLOSED requires PASS. These are synthetic assertions, not manufactured real evidence.

## Measurement and boundary contract

- exercise_response_minutes is elapsed scenario time from EXERCISE_STARTED to RESPONSE_RECORDED, including any explicitly advanced paused/stopped waiting. Missing response stays null. It is not live dispatch response, a safety benchmark or causal evidence.
- readiness_revisions and correction_revisions count corresponding record entries beyond the first in the selected branch. They do not count independently established institutional failures.
- completion_elapsed_minutes runs from DESIGNED to CLOSED, including preparation, review and correction time. Cancellation/abort have null completion duration. Open age is null for terminal states.
- The inherited correction_cycles field counts CORRECTION_RECORDED entries, including the initial entry; use correction_revisions for actual repeated records.
- live_dispatch_enabled=false, operational_readiness_certified=false, execution_authorized=false and legal_review=REQUIRED are explicit fixed boundaries.
- Stage/check records retain path revision, actor/reason and hashes. Snapshot restore selects another fictional branch without deleting history. Local SQLite is editable and actor identity is asserted; this is not a production emergency system or tamper-proof evidence ledger.

## API, tests and handoff

POST /api/scenarios accepts workflow=emergency. Existing control/report/export endpoints apply. GET /api/scenarios publishes the graph, two review states and phase-specific gate metadata. Existing permit/procurement/education/referral callers and stored histories retain their behavior.

    python -m unittest tests.test_emergency_scenarios -v
    python -m civic_portfolio export --output exercise-scenario.json
    python -m civic_portfolio backup --output exercise-backup.sqlite3
    python -m civic_portfolio --db exercise-backup.sqlite3 serve --port 8766

Ten tests cover every state/preset with both gate records, readiness hold/revision, correction role separation/revision, pause/stop/abort/cancel, response timing/missingness, exact restore, malformed/cross-workflow input atomicity, stale writes/backup isolation and API boundary fields. Browser CI covers both gates, failed checks, revised corrections, all presets, restore, persistence and mobile layout alongside prior workflows.

Full project-source import, actual exercise/readiness inventories, jurisdictional and accountable emergency authority, scenario safety controls, coverage/quality measures, multi-finding management, qualified operational/legal/security review and institutional adoption remain outstanding. No live emergency activity or completed institutional Project 022 is claimed. See [shared controls](SCENARIO-CONTROLS.md) for API and rollback details.
