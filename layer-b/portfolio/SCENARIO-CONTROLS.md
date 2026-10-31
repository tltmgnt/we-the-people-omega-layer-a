# Controllable use case — synthetic permit processing

The use case is one fictional permit moving through receipt, review, correction, inspection and a simulated disposition. This controller is a separate sandbox: no existing permit case, project completion, source review or legal hold is edited.

## Open the console

From the repository's layer-b directory, run Python 3.12:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/scenarios>, or choose **Controllable permit use case** on the portfolio home page. GitHub displays the source and these instructions; the interactive console runs locally.

Enter an identifier and reason/evidence for each command. Create a fictional SYN- scenario with a timezone-aware start time. No runtime dependency beyond the Python standard library is required.

## Every state in this use case

| Workflow state | Valid next workflow states | Other controls |
| --- | --- | --- |
| RECEIVED | IN_REVIEW, WITHDRAWN | Pause/resume/stop, manual clock, reset, presets, inspect/restore |
| IN_REVIEW | AWAITING_CORRECTION, INSPECTION, WITHDRAWN | Same controls |
| AWAITING_CORRECTION | IN_REVIEW, WITHDRAWN | Same controls; correction loop retained |
| INSPECTION | AWAITING_CORRECTION, DECIDED, WITHDRAWN | Same controls |
| DECIDED | None | Quality pass/failure and re-review, manual clock, reset, presets, inspect/restore |
| WITHDRAWN | None | Manual clock, reset, presets, inspect/restore |

Execution state is RUNNING, PAUSED, STOPPED or COMPLETED. PAUSE and STOP prevent workflow steps; RESUME is available for nonterminal paused/stopped scenarios. Terminal workflow states are COMPLETED and cannot resume; restore or reset creates another recorded scenario state instead.

Quality is UNREVIEWED, PASS or FAIL. Reviews are permitted only after DECIDED, including a failed review followed by a corrected passing review. These outcomes are fictional assertions, not authenticated acceptance.

All six workflow states are available through **Load state preset**. A preset replays a deterministic shortest valid path from RECEIVED, at 60 minutes per edge. PASS/FAIL presets apply only to DECIDED. The preset path and control event are retained; no workflow edge or institutional approval is fabricated.

The legal boundary is fixed: execution_authorized=false and legal_review=REQUIRED. Those fields have no override. This console covers the permit use case, not every unfinished portfolio domain.

## Hands-on example

1. Create SYN-PERMIT-DEMO, start 2026-01-01T00:00:00Z. Current state is RECEIVED / RUNNING / UNREVIEWED.
2. Pause. Workflow stepping becomes unavailable. Advance the scenario clock by 60 minutes: it remains paused, with 60 fictional elapsed minutes.
3. Stop, then resume. Step into IN_REVIEW with 60 minutes.
4. Step AWAITING_CORRECTION → IN_REVIEW → INSPECTION → DECIDED, with 60 minutes for each step.
5. Record a quality failure, then a quality pass. Inspect both review records. Quality never creates a real permit approval.
6. Inspect the earlier IN_REVIEW snapshot. Reset to RECEIVED, then restore that snapshot. Restoration reproduces its workflow, execution status, clock, path and review state in a new history event.
7. Load each of the six presets, including DECIDED / FAIL and WITHDRAWN. Reload to verify persistence.
8. Export the workspace or back up the SQLite database. Original domain permit cases remain unchanged.

## State, clock and history contract

- No background timer or automation runs. STEP advances fictional time by supplied positive integer minutes; TICK advances time without changing workflow. Both have bounded integers and an overall clock limit. Calendar overflow is rejected transactionally.
- PAUSE/STOP prevent workflow transitions, not an explicit manual TICK. This allows controlled experiments with waiting while work is halted. Tick remains available in terminal states to inspect post-disposition time.
- Decision elapsed time stops at the DECIDED event. Open age is current scenario minutes for nonterminal cases; withdrawn/decided cases have null open age. Stage durations include paused/stopped fictional waiting time and exclude terminal-state time. Effort is not inferred.
- PRESET/reset starts a fresh scenario path while retaining all prior control events. RESTORE copies an earlier snapshot into a new event with restored_from pointing to its sequence. Scenario time may move backward only through these explicit recorded controls.
- Every event retains actor, reason, parameters, resulting full state and its SHA-256. Later events also record the previous state's hash. Hashes help compare snapshots; locally editable SQLite is not a tamper-proof ledger.
- Optimistic versions reject stale control requests (409). Invalid commands, forbidden edges and unavailable controls return 400 with no mutation. Missing scenarios return 404. The shared loopback Host/origin/token controls apply.
- All state snapshots are scoped to one run. Restore cannot read a snapshot from another scenario. A run is bounded to 10,000 history events.
- User identifiers and reviews are local assertions. Use fictional data only. No personal records, real approvals or live agency actions.

## API and handoff

| Method and path | Purpose |
| --- | --- |
| GET /api/scenarios | Runs, state map, control schemas and local mutation token |
| POST /api/scenarios | Create isolated run: run_id, label, start_at, actor, note |
| POST /api/scenarios/{id}/commands | Current version, action, actor, note, parameters |
| GET /api/scenarios/{id}/report | Current timing, quality, state and fixed holds |

Actions are STEP, TICK, PAUSE, RESUME, STOP, REVIEW, PRESET and RESTORE. Parameter fields are published in the bootstrap response. Every command requires a reason. Snapshot inspection is read-only.

Export includes synthetic_scenarios run/event bodies plus the existing shared workspace export. Backups preserve all scenario history:

    python -m civic_portfolio export --output scenario-export.json
    python -m civic_portfolio backup --output scenario-backup.sqlite3
    python -m civic_portfolio --db scenario-backup.sqlite3 serve --port 8766
    python -m unittest tests.test_scenarios -v

Keep exports out of public git when the workspace contains private source material. Stop the app and retain an untouched backup before upgrades; restore a copy with the previous application version for rollback.

Tests cover every workflow preset, valid/invalid edges, pause/stop/resume, explicit paused clock advancement, correction-loop timing, terminal controls, all quality outcomes, reset/restore history, stale versions, invalid input atomicity, calendar limits, isolation, backup/export and HTTP controls. Browser CI walks the use case, all presets, quality outcomes, snapshot restore, persistence and mobile layout.

## Additional workflow: Project 019

The console now also supports a [procurement and contract-delivery use case](PROCUREMENT-LAB.md) with nine states and revision-specific acceptance holds. Select the workflow when creating a run. Omitted workflow and older stored bodies continue to default to permit. Reset targets each workflow's own initial state; snapshots remain scoped to the immutable run/workflow. The shared bootstrap publishes both workflow configurations. See the linked procurement handoff for closure rules and explicit checked CLOSED presets.

## Additional workflow: Project 020

The [education-service use case](EDUCATION-LAB.md) adds nine states for access, offers, service, follow-up, interruptions and withdrawal. Current continuity checks require an identifier distinct from both current service-start and follow-up recorders. Changed service/follow-up invalidates checks. All shared controls, historical snapshots and fixed holds apply. No learning assessment or student decisions are performed.

## Additional workflow: Project 021

The [fictional health-referral use case](HEALTH-LAB.md) adds eleven states for consent assertions, referrals/waiting, service/follow-up, interruption, decline and consent withdrawal. A separate current-revision continuity check is required before closure. Restore reproduces a fictional branch; it never renews real consent or authorizes any service. No clinical decisions or outcomes are assessed.

## Additional workflow: Project 022

The [controlled emergency-readiness exercise](EMERGENCY-LAB.md) adds eleven states, readiness checks before a simulated start and separate corrective-action checks before closure. Presets explicitly replay each gated check. Abort/cancel, all shared controls and snapshot restoration apply. No dispatch, emergency operations or readiness certification is performed.

## Additional workflow: Project 023

The [justice caseflow/remedy controller](JUSTICE-CONTROLS.md) adds fifteen states and three independent record-check gates. It supports remand/rehearing, revised remedies, reentry handoffs and both closure branches using existing controls. Existing observatory pilots and evidence stay separate. No judicial or release decisions, rights certification, remedy-effectiveness proof or recidivism assessment is performed.

## Portfolio-wide controls

All 44 defined workstreams (007–050) now have [project-specific state controls](CONTROLLED-PORTFOLIO.md), with [individual coverage and handoffs](CONTROL-COVERAGE.md). The six specialized workflows remain compatible; 38 catalog profiles add typed observations and counter-measures. Project 050 pins current completed observed scenario evidence. Projects 001–006 stay definition-blocked and all legal/live-execution holds remain fixed.
