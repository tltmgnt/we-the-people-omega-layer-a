# All defined workstreams — controllable synthetic portfolio

## Delivered scope and hard boundaries

All **44 defined workstreams, Projects 007–050**, now have configurable synthetic scenario controls. Six existing profiles retain their specialized logic; 38 additional profiles have project-specific state maps, checked closure/rework, typed measures/counter-measures and individual handoffs. Existing deeper domain labs remain available.

**Projects 001–006 remain definition-blocked.** Titles/scopes and the four foundational document mappings have not been confirmed. Their register records and source gaps stay visible; no invented project identity or accepted implementation is claimed.

[Coverage for all 50 slots](CONTROL-COVERAGE.md) lists every control/handoff and unresolved slot. The catalog is software coverage, not 44 independently accepted domain systems, validated methods, actual government collaboration or universal-standard certification. Full linked source documents remain unread except text directly supplied by the user. Project 023's full supplied specification remains preserved.

## Run

From layer-b, Python 3.12:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/scenarios>. The workflow selector lists all 44. Direct URLs use /scenarios?workflow=p024 (or another catalog key). The connected /initiative catalog provides both existing deeper prototype links and **Open state controls** for each defined project. The application uses only the Python standard library.

Create a unique SYN- run with a fictional actor, evidence/reason note and timezone-aware start timestamp. Use no personal, protected, live operational or confidential information. Local identifiers are unauthenticated assertions, and the loopback/token model is not production identity/access governance.

## Shared control contract

Every profile supports valid steps, pause/resume/stop, an explicit manual clock, every-state presets, reset, snapshot inspection and append-only restore. State maps differ by project, as documented in each handoff. A preset replays a shortest valid path and visibly inserts fictional checks where required. It does not fabricate real source evidence.

Checked closure requires a pass at the current review-path index by an identifier different from every current anchor recorder. Failure, missing checks or a rework transition prevents closure. WITHDRAWN and other terminal branches are separate from successful completion; they have null completion duration. Legal and execution holds never change.

Reset/preset creates a fresh fictional path; history remains. RESTORE copies an older complete snapshot into a new control event; it does not undo government action, restore real consent, or create legal authority. The workflow is immutable per run. Old permit/procurement/education/referral/exercise/justice runs and snapshots remain compatible.

Profile definitions live in scenario-profiles.json and are validated for IDs, stage references, reachability, terminal states, review anchors and metric kinds at startup. They are editorial contracts derived from registered titles and proposed profiles, not transcriptions of unavailable source documents.

## Typed measurements and counter-measures

The 38 catalog profiles include two declared contracts each. Their period is the current fictional branch, owner is a local assertion, all live/person-level data is excluded, uncertainty is unverified synthetic input, and corrections append new observations. Every contract includes definition, unit, numerator/denominator interpretation where applicable, missingness, counter-metric and correction process.

| Kind | Accepted known value | Missing and invalid values |
| --- | --- | --- |
| COUNT | Integer 0–10^9 | Missing stays null with a reason; booleans, fractions and negatives rejected |
| INTEGER_MINOR_UNITS | Integer 0–10^12 in separately declared minor units | No cross-category accounting total; missing stays null |
| MINUTES | Finite nonnegative number ≤10^7 | NaN, infinity, booleans, strings and negative values rejected |
| RATIO | Explicit integer numerator and positive denominator, each ≤10^9; numerator ≤ denominator | A declared proportion only; no invented denominator or direct value field |

Use **Record fictional observation** with the selected contract and global evidence note. For a missing measurement leave value/numerator/denominator blank and supply the missing reason. Known zero is preserved as zero. Ratios calculate from the supplied numerator/denominator. A counter-measure stays separate; no composite score, institutional ranking, causal improvement or method-validation claim is inferred.

Observations retain actor/note, exact contract hash and current path index. Further workflow steps mark older observations stale; changing the contract marks it stale independently. A corrected observation supersedes the displayed value while preserving earlier history. Reset/preset clears measurements on the selected branch; snapshot restoration restores the earlier measurement with that branch.

Existing specialized labs retain their own measurement contracts. These catalog observations are not a replacement for validated domain data or independently verified source records.

## Project 050 — evidence-pinned cross-layer capstone

The capstone rehearses Layer A hold → B process record → C outcome assertion → D evidence → E rollback record. It uses the same workflow controls but has an additional evidence gate:

1. Complete a non-capstone source run such as p024 with a current passing check.
2. Record a known observation at that source's completed path. Note its latest snapshot sequence/version.
3. Create p050 and use **Attach scenario snapshot** with source ID and exact sequence. Self-attachments and nested capstones are rejected.
4. The capstone pins source workflow, sequence and state SHA-256. Closure requires at least one intact, **current**, completed source snapshot with a current known observation and unchanged metric contract, in addition to its own record-review pass.
5. Advancing/changing the source makes the attachment stale. Reattach its latest qualifying snapshot and record a fresh capstone check. ATTACH invalidates the current capstone review.
6. A CLOSED capstone preset must already have qualifying source evidence and reuses those exact references. It cannot invent a source run, completion or measurement. Other presets start a fresh branch and clear attachments.
7. A historically closed capstone remains in history if a source later changes; capstone_evidence_current becomes false. It is not silently rewritten or represented as fresh acceptance.

The bundle is traceable synthetic evidence, not proof of actual outcome effectiveness or a real Layer A clearance. **layer_a_status remains LEGAL_REVIEW_REQUIRED and execution_authorized remains false**, including at CLOSED with every check passed.

## API

Existing routes remain:

| Method and path | Purpose |
| --- | --- |
| GET /api/scenarios | All 44 configurations, states, contracts, runs and mutation token |
| POST /api/scenarios | Create a run with immutable workflow key |
| POST /api/scenarios/{id}/commands | Versioned STEP/TICK/PAUSE/RESUME/STOP/REVIEW/PRESET/RESTORE/OBSERVE/ATTACH |
| GET /api/scenarios/{id}/report | Current timing, observations/freshness, references and fixed holds |

OBSERVE parameters are metric_id, value, numerator, denominator, missing_reason; use null for inapplicable or missing numbers. ATTACH parameters are source_run_id and source_sequence and are available only in p050. Every command needs actor, evidence/reason note and current version. Invalid/contradictory input is transactional; stale versions return 409.

No arbitrary state forcing, live service connection, source acceptance, legal approval, vendor award, personnel decision, school/learner ranking, autonomous judicial/clinical decision, grid control, dispatch or actual analytical-agent execution is performed.

## Verification and handoff

    python -m unittest tests.test_controlled_portfolio -v
    python -m unittest discover -s tests -v
    python -m civic_portfolio export --output controlled-portfolio.json
    python -m civic_portfolio backup --output controlled-portfolio.sqlite3
    python -m civic_portfolio --db controlled-portfolio.sqlite3 serve --port 8766

The catalog suite exercises all 38 new profiles, every state preset, complete checked paths, recorder separation, failed/revised checks, measurement bounds/missingness/freshness, source-contract changes, capstone source pinning/staleness, self/nested references, snapshot restore, stale writes, backup/export and HTTP/token controls. Browser CI covers all additional profiles and presets, measurements, capstone rejection/recovery, persistence and mobile layout alongside all previous tests.

Export/backup preserves state, measurements, source references and full immutable control history. Keep exports private if the shared workspace contains private source text; synthetic runs do not sanitize other workspace contents. Stop the application and retain an untouched backup for rollback. Locally editable SQLite and asserted actors are not tamper-proof records or authenticated approval.

## Outstanding acceptance

Software scenario coverage is delivered for 007–050. Remaining substantive work includes full source import/review, confirming 001–006, project-specific data/operating contracts, actual method benchmarks and agent execution where appropriate, qualified rights/legal/security/professional review, real evaluation and institutional acceptance. The shared framework and these scenarios remain proposed methods and fictional demonstrations, not completed government programs.

## Ready-to-inspect example batch

The [one-action demo loader](DEMO-LOADER.md) creates 44 completed fictional examples, sample catalog observations and a linked capstone through the normal controls. It is atomic, rejects collisions and preserves later edits on repeat loading. The CLI command is `python -m civic_portfolio demo-scenarios --batch-id SYN-DEMO-V1 --actor "DEMO INITIATOR"`. Existing source/project/domain records and all legal/live holds remain unchanged.
