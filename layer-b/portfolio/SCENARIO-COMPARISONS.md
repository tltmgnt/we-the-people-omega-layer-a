# Compare baseline and alternative scenario snapshots

This adds a read-only-source comparison workspace. It saves immutable comparisons of **two fictional snapshots**, not an experiment, causal estimate or institutional performance judgment.

## Open and prepare a pair

From layer-b:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/compare-scenarios>, or use **Compare scenario snapshots** in the controller.

1. [Load fictional examples](DEMO-LOADER.md), then select a catalog run such as SYN-DEMO-V1-024.
2. Inspect its latest snapshot sequence and known referral_wait_minutes value (the demo value is 30).
3. Enter an operator identifier/evidence note and append an observation of 15 minutes on the same completed path. Both snapshots stay in history.
4. In the comparison page, choose the same run twice, with baseline set to the earlier sequence and alternative set to the later sequence.
5. Enter a unique SYN- comparison ID and purpose/limitations, then save.
6. The difference is -15 supplied fictional minutes. This does **not** establish improved access, effectiveness or a causal intervention.

You can instead create two run namespaces/batches. Same-workflow snapshots are required; case mix, population, sampling and actual source validity are not controlled.

## Comparison rules

| Condition | Behavior |
| --- | --- |
| Different workflows | Creation rejects without changing either source |
| Different workflow stages or execution states | Raw values remain visible; numeric deltas are withheld |
| Different CLOSED predecessor/review branches | Numeric deltas are withheld (for example justice remedy versus reentry) |
| Missing known measurements | Null stays unknown; no invented zero or delta |
| Observation from an earlier path revision | Its metric delta is withheld |
| Observation contract differs from the comparison's frozen contract | Delta is withheld and that source unit is unverified |
| Baseline quality PASS lost in alternative | Explicit warning; speed is not treated as improvement |
| Later source activity | Snapshot pins and saved arithmetic do not change; source_current becomes false and the comparison is historical |
| Later workflow definition change | Workflow fingerprint warning; saved arithmetic remains historical |
| Later catalog contract change | Frozen definitions/units are retained, current-contract warning is shown |
| Missing/changed pinned snapshot | Integrity warning and UI numeric-delta withholding; new comparison cannot use a hash-mismatched source |

Delta is **alternative minus baseline**. Neither sign is automatically favorable; main/counter-measures remain separate. Ratio numerator/denominator values are retained for each side. No p-values, significance, causal effect, composite score, ranking or automated improvement decision is produced.

Timing uses scenario-relative minutes, so it does not subtract unrelated calendar start dates. Completion duration stops at each completion milestone; manual post-completion clock advancement affects clock_minutes but does not rewrite completion_minutes. Withdrawal is not successful completion and has null completion duration/open age. Necessary preparation, safeguards and case differences require independent interpretation.

## Frozen records and current diagnostics

Each immutable comparison stores creator, purpose/limitations, timestamp, workflow/project and workflow-definition fingerprint, source run IDs/sequences/state hashes, current-at-creation flags, full metric definitions at creation, arithmetic and fixed legal boundaries. Reusing the ID rejects; use another ID for another comparison.

Comparing reads source records and adds only a comparison row/audit event. It never edits a source run, restores a branch, records acceptance or creates legal authority. A source that advances remains available as the originally selected historical snapshot. Saved arithmetic and frozen units are retained even after newer definitions appear; warnings distinguish historical applicability from current catalog/source state.

Fingerprint checks detect ordinary snapshot inconsistencies; locally editable SQLite is not a tamper-proof ledger, and actor identifiers are not authenticated signatures. If old data was already contract-incompatible at creation, its unit/delta remains withheld. Currentness is not proof of truth or effectiveness.

causal_effect_estimated=false, case_mix_controlled=false, execution_authorized=false and layer_a_status=LEGAL_REVIEW_REQUIRED remain fixed. A comparison of fictional records does not establish legality, fairness, safety, benefits, actual method performance or institutional adoption.

## API and handoff

| Method and path | Purpose |
| --- | --- |
| GET /api/scenario-comparisons | Saved comparisons, source runs and local mutation token |
| POST /api/scenario-comparisons | Save comparison ID, baseline run/sequence, alternative run/sequence, actor and note |
| GET /api/scenario-comparisons/{id} | Frozen result plus current integrity/source/catalog flags |

GET /compare-scenarios?comparison=SYN-COMPARISON opens a saved comparison. POST uses the existing loopback Host/origin/token restrictions. IDs and references are validated, and comparison creation is transactional. Workspace export includes synthetic_scenarios.comparisons, and SQLite backups preserve comparisons plus all source snapshots.

    python -m unittest tests.test_scenario_comparisons -v
    python -m civic_portfolio export --output compared-scenarios.json
    python -m civic_portfolio backup --output compared-scenarios.sqlite3

Twelve tests cover arithmetic/source isolation, unknown versus zero, immutable historical results, workflow/phase/branch incompatibility, path/contract freshness, frozen units, quality-pass loss, snapshot integrity, immutable IDs/invalid references, backup/export and guarded HTTP. Browser CI covers creation, arithmetic, note escaping, reload, source advancement without result rewriting and mobile layout.

Use only fictional data. Source requirements, proper study/evaluation design and qualified institutional review remain outstanding. [Shared controller](CONTROLLED-PORTFOLIO.md).
