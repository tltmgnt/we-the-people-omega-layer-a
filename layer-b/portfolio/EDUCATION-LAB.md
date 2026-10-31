# Project 020 — Controllable education-service access and continuity

A bounded synthetic use case based on the registered title/editorial plan. The linked full source is unread. This software records fictional access/delivery milestones, interruptions and continuity checks. It makes no student decisions, evaluates no learning effectiveness and ranks no learners or schools.

## Open and run

From layer-b, Python 3.12:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/scenarios?workflow=education>. Select **Project 020 · Education-service access and continuity**, then create SYN-EDUCATION-DEMO with a fictional label, start time, actor identifier and note. Do not enter student names, real enrollment records, disability/health details or protected school data.

The same console supports permit and procurement runs without rewriting their history. Education is an immutable workflow choice per run. Reset returns this workflow to REQUEST_RECORDED.

## All nine states

| State | Valid next states |
| --- | --- |
| REQUEST_RECORDED | ACCESS_REVIEW, WITHDRAWN |
| ACCESS_REVIEW | SERVICE_OFFERED, WITHDRAWN |
| SERVICE_OFFERED | SERVICE_STARTED, ACCESS_REVIEW, WITHDRAWN |
| SERVICE_STARTED | FOLLOW_UP_RECORDED, INTERRUPTED, WITHDRAWN |
| INTERRUPTED | SERVICE_OFFERED, WITHDRAWN |
| FOLLOW_UP_RECORDED | CONTINUITY_REVIEW, INTERRUPTED, WITHDRAWN |
| CONTINUITY_REVIEW | CLOSED after current passing check, INTERRUPTED, WITHDRAWN |
| CLOSED | None |
| WITHDRAWN | None |

ACCESS_REVIEW records a fictional barrier/process review, not an eligibility or admission determination. SERVICE_OFFERED is not proof that access occurred. SERVICE_STARTED is a recorder's assertion, not verified learning.

Use pause/resume/stop, manual clock, valid steps, any-state presets, reset, snapshot inspection and append-only restore. Withdrawal is terminal and excluded from completion timing. Completion remains a fictional service record, not a learning outcome.

## Example and continuity check

1. Step ACCESS_REVIEW → SERVICE_OFFERED → SERVICE_STARTED → FOLLOW_UP_RECORDED → CONTINUITY_REVIEW, with 60 fictional minutes per edge.
2. Use separate identifiers for the service-start recorder and follow-up recorder if desired. The continuity checker must differ from **both** current recorders. These identifiers are unauthenticated local assertions; the software does not establish professional independence.
3. Unreviewed or failed continuity cannot close. A current pass enables CLOSED.
4. Instead, record INTERRUPTED and repeat SERVICE_OFFERED → SERVICE_STARTED → FOLLOW_UP_RECORDED → CONTINUITY_REVIEW. Every new transition clears the current check, so the earlier pass cannot close a new service/follow-up revision.
5. Record a fresh distinct-recorder passing check, then close. Inspect the interruption and earlier reviews in history.
6. Restore the earlier checked CONTINUITY_REVIEW snapshot. It restores that exact service/follow-up branch and its check together, into a new event.
7. Try all nine presets. CONTINUITY_REVIEW allows UNREVIEWED, PASS or FAIL. CLOSED requires PASS and explicitly contains a fictional SYN-PRESET-CHECKER record, separate from SYN-PRESET-RECORDER. It never fabricates real educational evidence.

Checks require RUNNING execution; paused/stopped checks are blocked until resume. Manual TICK remains available while paused/stopped. No autonomous processing occurs.

## Measurement and boundary contract

- Initial request to first SERVICE_STARTED minutes is reported separately from initial request to CLOSED minutes. First-start time does not imply sustained access.
- Interruptions count INTERRUPTED transitions in the currently selected branch. Stage durations include fictional waiting during pause/stop. Previous branches remain in immutable control history.
- Open age is null for CLOSED/WITHDRAWN; withdrawals have null completion duration. No denominator, access-equity rate, attendance rate, learning score, outcome causality or exclusion measure is inferred from a single fictional run.
- learning_outcomes_assessed=false, execution_authorized=false and legal_review=REQUIRED remain explicit. A continuity pass is an assertion of scenario review, not assessed learning, admission, accommodation compliance or institutional acceptance.
- No personal identity, eligibility, grades, ranking or school evaluation fields are provided. Free-text fields cannot automatically prevent sensitive information entry: use synthetic data only.
- Snapshot hashes, optimistic versions, transaction validation, audit/export/backup and loopback/token/origin restrictions are inherited from the [scenario controls](SCENARIO-CONTROLS.md). Local SQLite is editable and identities are asserted; this is not a production student system.

## API, tests and handoff

POST /api/scenarios supports workflow=education. All existing control commands and snapshot/export APIs apply. GET /api/scenarios publishes the state graph and review states.

    python -m unittest tests.test_education_scenarios -v
    python -m civic_portfolio export --output education-scenario.json
    python -m civic_portfolio backup --output education-backup.sqlite3
    python -m civic_portfolio --db education-backup.sqlite3 serve --port 8766

Eight tests cover every state, checked closure, both recorder exclusions, interruption invalidation, pause/stop/manual clock, withdrawal and missing completion/outcomes, exact snapshot restore, malformed/cross-workflow inputs, stale writes and backup isolation. Browser CI exercises the review holds, interrupted service cycle, all presets, restore, persistence and mobile layout alongside all existing flows.

Full project-source import/review, actual program/access data, lawful subgroup definitions, privacy/security/retention governance, meaningful learning/quality measures, qualified educational review and institutional adoption remain outstanding. Project 020 is not represented as institutionally complete.
