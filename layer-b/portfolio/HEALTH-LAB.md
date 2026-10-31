# Project 021 — Controllable health-service referral and continuity

A bounded **fictional administrative referral exercise**, based on the registered title/editorial plan. The full linked source remains unread. This prototype does not process patient records, provide medical advice, diagnose, triage, determine eligibility, select treatment or make actual referrals.

## Open the use case

From layer-b, Python 3.12:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/scenarios?workflow=health>, or select **Project 021 · Health-service referral and continuity**. Create SYN-HEALTH-DEMO with a fictional label/start time and actor/note.

Do not enter names, contacts, actual consent records, symptoms, diagnoses, medical records or emergency requests. All milestones, consent labels and checks are unauthenticated local assertions. This loopback single-workspace app is not a healthcare system or a production privacy/access-control solution.

## All eleven states

| State | Valid next states |
| --- | --- |
| REQUEST_RECORDED | CONSENT_RECORDED, DECLINED |
| CONSENT_RECORDED | REFERRAL_RECORDED, CONSENT_WITHDRAWN, DECLINED |
| REFERRAL_RECORDED | WAITING, CONSENT_WITHDRAWN, DECLINED |
| WAITING | SERVICE_STARTED, REFERRAL_RECORDED, CONSENT_WITHDRAWN, DECLINED |
| SERVICE_STARTED | FOLLOW_UP_RECORDED, INTERRUPTED, CONSENT_WITHDRAWN |
| INTERRUPTED | REFERRAL_RECORDED, CONSENT_WITHDRAWN, DECLINED |
| FOLLOW_UP_RECORDED | CONTINUITY_REVIEW, INTERRUPTED, CONSENT_WITHDRAWN |
| CONTINUITY_REVIEW | CLOSED after current passing check, INTERRUPTED, CONSENT_WITHDRAWN |
| CLOSED, DECLINED, CONSENT_WITHDRAWN | None |

The consent milestone ensures that the synthetic path cannot skip its declared consent step; it does not establish legally valid consent. REFERRAL_RECORDED is not an actual handoff, and SERVICE_STARTED is not evidence of benefit or clinical effectiveness.

Every state has the shared applicable pause/resume/stop, clock, step, preset, reset, inspection and restore controls. Decline and recorded withdrawal are terminal, not successful completion. Reset targets REQUEST_RECORDED for this workflow. Existing permit, procurement and education runs retain their own state maps and history.

## Exercise the success and failure paths

1. Step CONSENT_RECORDED → REFERRAL_RECORDED → WAITING → SERVICE_STARTED → FOLLOW_UP_RECORDED → CONTINUITY_REVIEW, at 60 fictional minutes per step.
2. Closure is unavailable before a passing current-revision check. The continuity checker identifier must differ from both the latest service-start recorder and latest follow-up recorder. Identifiers do not establish professional independence.
3. Record a failure, observe the closure hold, then record a pass.
4. Instead of closing, record INTERRUPTED → REFERRAL_RECORDED → WAITING → SERVICE_STARTED → FOLLOW_UP_RECORDED → CONTINUITY_REVIEW. A fresh service/follow-up cycle invalidates the prior check and requires another pass.
5. Close after a fresh check, or record CONSENT_WITHDRAWN. Withdrawal blocks further workflow steps and resume. It does not erase the earlier history.
6. Restore the earlier checked continuity snapshot into a new history event. This copies the **fictional branch**, including its earlier consent assertion; it never reinstates a real person's consent. No real consent or service authority exists in any branch.
7. Try every state preset. CONTINUITY_REVIEW supports UNREVIEWED/PASS/FAIL. CLOSED requires PASS and explicitly records a fictional preset checker distinct from preset recorders. No real evidence is generated.

No background timer or automated referrals run. Pause/stop blocks workflow steps/checks, while explicit manual TICK can advance fictional waiting time.

## Diagnostic contract

- First-service elapsed minutes run from initial request to first SERVICE_STARTED on the current branch; absence stays null. This is not referral completion or clinical effectiveness.
- referral_wait_minutes is summed residence in WAITING, including fictional paused/stopped time, across repeated referral cycles. It is not all pre-service time or a legal/clinical waiting-time standard.
- repeat_referrals counts REFERRAL_RECORDED entries after the first. service_interruptions counts INTERRUPTED transitions. These are scenario diagnostics, not unmet-need prevalence, quality scores or causal findings.
- Completion elapsed minutes exists only for CLOSED. Decline/consent withdrawal have null completion duration and open age. No patient/population denominators or health outcome estimates are inferred.
- consent_status is NOT_RECORDED, ASSERTED_ONLY or WITHDRAWAL_RECORDED. It is a branch label, not a valid authorization record.
- clinical_outcomes_assessed=false, execution_authorized=false and legal_review=REQUIRED are fixed boundaries. A passing continuity check is not clinical approval or evidence of treatment benefit.
- Review validity is tied to the exact current path revision. Source snapshots are scoped to the immutable run/workflow; hashes, actor/reason, optimistic versions, transaction rollback, audit/export/backup and restoration follow the [shared scenario controls](SCENARIO-CONTROLS.md).

## API, verification and handoff

POST /api/scenarios accepts workflow=health. Shared command/report/export endpoints apply. GET /api/scenarios publishes the eleven-state graph, terminal states and continuity review state.

    python -m unittest tests.test_health_scenarios -v
    python -m civic_portfolio export --output referral-scenario.json
    python -m civic_portfolio backup --output referral-backup.sqlite3
    python -m civic_portfolio --db referral-backup.sqlite3 serve --port 8766

Nine tests cover all state presets, the consent milestone/withdrawal, separate current service/follow-up checks, interruption and repeated referral, waiting-clock/decline, exact fictional restore, malformed/cross-workflow inputs, stale writes/backup isolation and explicit nonclinical API fields. Browser CI covers the same core walkthrough, failure/recovery, all states, persistence and mobile layout.

Full project-source import/review, real referral/service-directory integration, valid consent/access/retention governance, unmet-need and service-quality measures, qualified clinical/privacy/legal review and institutional adoption remain outstanding. No real health-service intervention or completed institutional Project 021 is claimed.
