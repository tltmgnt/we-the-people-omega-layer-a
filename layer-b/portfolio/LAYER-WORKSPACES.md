# Dedicated C/D/E synthetic workspaces

Start `python -m civic_portfolio serve`, then follow **Layers C–E: outcomes, evidence and learning** on the portfolio home page, or open `/layers` at the local application address. These are dedicated prototypes hosted in the existing Layer B application, using the same loopback/token protections, SQLite backup and workspace export. They do not replace or clear Layer A review, or turn B scenario observations into verified real outcomes.

## Contracts and evidence flow

| Layer | Records and controls | Boundary |
| --- | --- | --- |
| D — Intelligence and Evidence | Exact-text SHA-256 evidence revisions, origin, limitations, confidence A/B/C, corroborating/verification references, separate pass/fail revision checks | Confidence and reviewer identity are user assertions; hashes are unsigned; no source authentication or executed analytical agents |
| C — Human and Community Outcomes | Immutable study definitions, units, aggregate cohort, exclusions, uncertainty, owner and counter-measure; append-only baseline/follow-up observations, source revision pins and separate pass/fail checks | Fictional aggregate data; descriptive differences, no causal effect, significance, case-mix adjustment or verified human benefit |
| E — Transformation and Institutional Learning | Immutable scope/owner/resources/continuity/rollback plan linked to C studies; checked rehearsal phases; reopen and rollback history; evidence/outcome context fingerprints | Local rehearsal only; no actual intervention, public release, institutional adoption or authority |

D evidence → C pinned observations → E context-pinned rehearsal. A remains `LEGAL_REVIEW_REQUIRED`; `execution_authorized` always remains false. B scenario controls and domain labs remain separate; cross-navigation does not automatically import or certify their data.

## A worked fictional use case

1. Select **D · Record/revise evidence**. Use `SYN-ACCESS-SOURCE`, a fictional aggregate source text, origin, C confidence and explicit limitations. Initial expected revision is 0; changing to an existing evidence ID selects its current revision. Exact text, including surrounding whitespace, is preserved and hashed. A confidence needs an asserted verification reference; B needs distinct corroborating references. Neither claim is independently authenticated.
2. A different local identifier records a passing **D · Check current evidence** for that revision. A failing check can revoke it. Local identity separation is a record-level control, not authentication.
3. Define **C · Define outcome study**: primary proportion “completed / eligible requests”, unit “fraction”; counter count “repeat visits”, unit “visits”; fictional cohort, exclusions, uncertainty and owner. Changing this contract requires a new study ID.
4. Record a baseline: 8/10 completed, 2 repeat visits, window January 1–2; follow-up: 9/10, 1 repeat visit, window January 2–3. Choose the current source pin for each. Record at/after window end and study creation, then have a different identifier check each observation using its event sequence in the report.
5. The C report shows +0.1 fraction (10 percentage points) and −1 repeat visit. It does not infer a causal improvement. Every observed group needs both windows and known primary/counter values. An unknown count needs a missing-data reason, not zero. Counts use a null denominator; proportions need a positive integer denominator. Overlapping/reversed windows, incomplete pairs, stale evidence, failed/missing checks and unknown measures withhold deltas/readiness. No across-group summary or institutional rank is computed.
6. Define an E rehearsal with the study selected and an explicit owner/resources/continuity/rollback plan. Record DESIGNED and check it with a different identifier. Continue through the sequence below. A passing separate check of the current phase is required before advancing. REHEARSAL_RECORDED and later also require all linked studies to have complete current checked pairs. Readiness means local record completeness, not effective treatment or deployment approval.
7. Revise the D evidence. The old C pins are retained but become stale; C readiness is false and prior E events are marked stale. A new phase/check cannot silently reuse the old context. Recheck D, append corrected C observations using current pins and separately check them; then REOPEN the E rehearsal and repeat its phases/checks. Every C event, including a check revocation, conservatively changes E context.

## Every rehearsal state

| Current state | Allowed controls |
| --- | --- |
| DRAFT | Record DESIGNED; REOPEN retains history and remains DRAFT |
| DESIGNED | CHECK pass/fail; after a current passing separate check, record BASELINE_RECORDED; REOPEN |
| BASELINE_RECORDED | CHECK pass/fail; after a current passing separate check and complete C pairs, record REHEARSAL_RECORDED; REOPEN |
| REHEARSAL_RECORDED | CHECK pass/fail; after a current passing separate check, record EVALUATION_RECORDED; ROLLBACK or REOPEN |
| EVALUATION_RECORDED | CHECK pass/fail; after a current passing separate check, record LEARNING_RECORDED; ROLLBACK or REOPEN |
| LEARNING_RECORDED | CHECK pass/fail; ROLLBACK or REOPEN; no further forward phase |
| ROLLED_BACK | REOPEN to DRAFT; history remains |

Each phase uses the current C versions and D revision/review context; changes invalidate earlier checks. CHECK targets the current recorded phase sequence, never an arbitrary historical event. ROLLBACK is a local withdrawal record and does not undo real-world actions. REOPEN does not delete evidence or authorize anything. Recorder/checker identities, reason and RFC3339 time are required; events cannot be backdated before existing activity. Stale writes fail without adding partial records/audit entries. Study and trial contracts are immutable; observations are corrected by appending replacements for the same phase/group, preserving history and requiring new checks.

## API and persistence

- `GET /api/layers`: evidence revisions/checks, study/trial contracts/events, schemas, phase list and local mutation token.
- `POST /api/layers/{kind}`: one of `EVIDENCE`, `EVIDENCE_REVIEW`, `STUDY`, `OBSERVATION`, `OUTCOME_REVIEW`, `TRIAL`, `TRIAL_EVENT`. Exact required keys are returned by `schemas`, plus `actor`, `note`, `at`. EVIDENCE_REVIEW uses current `revision`; EVIDENCE uses `expected_revision` (0 when new); existing C/E records use current `version`. Unknown keys and invalid/missing fields fail.
- `GET /api/layers/studies/{id}` and `/api/layers/trials/{id}`: recomputed reports with current evidence/readiness, reasons for withholding results, history and legal holds.
- `GET /api/export`: `synthetic_layers` includes evidence, studies, trials and activity (stored JSON bodies). SQLite backup/reopen preserves the same records. Existing selected scenario review ZIPs do **not** include this C/D/E workspace data.

Identifiers must use `SYN-` and uppercase letters/digits/hyphens. No personal, sealed or confidential data should be entered. The tool provides no redaction, protected-data authorization, identity verification, production access control or retention enforcement. Source pins are explicit local references, not automatic ingestion from Google Docs or B operational datasets.

## Validation and outstanding work

Backend tests cover exact-byte hashes, confidence requirements, revision/review revocation, chronology, complete/missing/zero measurements, denominator validation, overlapping windows, superseded observations, source/outcome invalidation, phase checks, rollback/reopen, atomic stale writes, HTTP/token guards and export/backup persistence. Browser checks exercise the D→C→E use case, failed stale advancement, reopened history, reload persistence and mobile layout.

These prototypes implement only the conversation-supplied five-layer summaries and a bounded fictional use case. Full A–E source import/review, finalized project definitions 001–006, validated analytical methods, authenticated qualified review, real data evaluation, legal/security/accessibility acceptance and institutional authorization/adoption remain outstanding. [Architecture index](../../Docs/Architecture/README.md).
