# Project 019 — Controllable procurement and contract-delivery use case

This is a bounded **synthetic scenario prototype** based on the registered title and editorial plan. The linked full project source remains unread. It models milestone recording, delivery correction, an acceptance check and simulated closure/cancellation. It does not solicit bids, evaluate vendors, award contracts, spend money or certify legal/procurement compliance.

## Open and control the use case

From layer-b, Python 3.12:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/scenarios?workflow=procurement>. Choose **Project 019 · Procurement and delivery** when creating a run. The connected 50-project catalog links directly to this workflow. Existing permit runs and their stored snapshots remain compatible.

Create SYN-CONTRACT-DEMO with a fictional label, start timestamp, recorder identifier and reason. All commands need an attributable fictional reason. No real vendor details, bids, contracts, credentials or protected information should be entered.

## All nine workflow states

| State | Valid next states |
| --- | --- |
| DRAFT | SOLICITATION_RECORDED, CANCELLED |
| SOLICITATION_RECORDED | EVALUATION_RECORDED, CANCELLED |
| EVALUATION_RECORDED | CONTRACT_RECORDED, CANCELLED |
| CONTRACT_RECORDED | DELIVERY_RECORDED, CANCELLED |
| DELIVERY_RECORDED | ACCEPTANCE_REVIEW, CANCELLED |
| ACCEPTANCE_REVIEW | CORRECTION_REQUESTED, CLOSED (checked), CANCELLED |
| CORRECTION_REQUESTED | DELIVERY_RECORDED, CANCELLED |
| CLOSED | None |
| CANCELLED | None |

These are scenario records, not actual procurement acts. Each state has pause/resume/stop, manual clock, valid stepping, preset, reset, inspection and snapshot-restore controls as applicable. CLOSED/CANCELLED are terminal and cannot resume. Reset returns this workflow to DRAFT, while permit reset still returns to RECEIVED.

### Acceptance, failure and corrected delivery

1. Record the path through solicitation, evaluation, contract, delivery and ACCEPTANCE_REVIEW, using 60 fictional minutes per edge.
2. CLOSED is unavailable until a passing check is recorded. A checker identifier must differ from the actor who recorded the current DELIVERY_RECORDED event. Identifiers are local assertions, not authenticated independent reviewers.
3. Record a failure with the checker identifier. Closure remains blocked. Record a passing check; closure becomes available.
4. Instead, step to CORRECTION_REQUESTED and record another delivery. This clears current quality and the prior acceptance pin. On returning to ACCEPTANCE_REVIEW, the old pass cannot close the new revision. A new, distinct-recorder check is required.
5. Close after a fresh pass, or cancel. A closed result is still a fictional assertion and never authorizes payment or establishes that goods/services reached the public.

Checks are tied to the exact acceptance path index in the current snapshot. Later delivery/correction transitions invalidate it even if the same actor or scenario assumptions recur. Reviews require RUNNING execution; pause/stop must be resumed first. A later failure replaces an earlier pass for gating while preserving review history.

### Presets and restoration

Every state is reachable by a shortest valid preset path at 60 minutes per edge. ACCEPTANCE_REVIEW can be loaded as UNREVIEWED, PASS or FAIL. CLOSED requires a PASS preset; the controller explicitly inserts a fictional check by SYN-PRESET-CHECKER, distinct from SYN-PRESET-RECORDER, before the closing edge. This check is visible in the snapshot and is not real evidence. An unchecked/failed CLOSED preset is rejected.

Inspect any earlier state snapshot and restore it into a new append-only control event. Restoring an exact acceptance snapshot restores that snapshot's check and delivery revision together. Original history is never deleted. The workflow type is immutable per run; restoring does not convert a permit run into a procurement run.

## Measurement and safeguards

- Manual UTC scenario clock, no background processing. Pause/stop blocks workflow transitions and checks; explicit TICK still advances fictional waiting time.
- Completion elapsed minutes run from initial DRAFT to CLOSED; cancellation is excluded and has null completion duration. Open age is separately null for terminal states. No service-time benchmark, deadline compliance, contract-value variance or real-world procurement performance is inferred.
- Correction cycles count CORRECTION_REQUESTED events in the current branch. Stage minutes include fictional paused waiting and exclude terminal-state time. Restoring/presetting selects another branch while preserving all control history.
- Each event retains actor, reason, parameters, state, hashes and source snapshot reference for restoration. Optimistic versions, validation, transaction rollback and shared loopback/token/origin controls apply.
- execution_authorized remains false and legal_review REQUIRED. No award decision, vendor ranking, competition score, integrity allegation or real financial action is produced.

The same [scenario API and handoff](SCENARIO-CONTROLS.md) applies. POST /api/scenarios accepts workflow=procurement; omitting workflow preserves the legacy permit default. GET /api/scenarios publishes each workflow's states, terminal states, review states and initial state. Older stored run bodies without workflow are read as permit without rewriting their historical snapshots.

## Verification and outstanding work

    python -m unittest tests.test_procurement_scenarios -v

Eight procurement tests cover all states, closed-preset evidence, distinct checker/current-revision closure, correction invalidation, pause/stop/cancellation, snapshot restore, invalid cross-workflow commands, legacy compatibility, stale commands and backup/restore. Browser CI covers the acceptance holds, changed-delivery check, all nine presets, mobile layout and persistence, in addition to the permit walkthrough.

Full source import/review, actual solicitation/competition and contract/change-order records, milestone baselines and delivery variance, qualified procurement/legal/security acceptance, institutional adoption and official data integration remain outstanding. The software delivers a controllable use case; Project 019 is not claimed institutionally complete.
