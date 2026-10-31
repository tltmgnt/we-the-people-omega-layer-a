# Project 016 — synthetic rights evidence and review intake

## Delivered scope

The local application records fictional proposal intake, A1–A7 domain-screening assertions, exact-text evidence snapshots, unassessed candidate authority references, review questions, alternative explanations, limitations and local response/challenge history. It produces a schema-compatible Layer A intake draft plus a companion evidence bundle. This prototype follows the [editorial plan](plans/016.md) and [existing Layer A assurance contract](../../Docs/Assurance/review-gate.md), not the unread linked project source.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/rights>. Restart an existing server to add the routes/tables. Existing workspace records remain intact. No evidence, applicability claim or review result is inserted automatically; each new case starts with seven UNASSESSED domains and a legal-review hold.

## Fictional walkthrough

1. Enter an operator identifier. Create `SYN-RIGHTS-001`, proposal `SYN-PROPOSAL-001`, a fictional institution/jurisdiction and a bounded fictional summary, at `2026-01-01T00:00:00Z`.
2. Append evidence `SYN-EVIDENCE-001` at `01:00:00Z` with fictional origin and full scenario text. The exact UTF-8 text received by the application is retained and SHA-256 hashed; pasted text is not proof of an original document's authenticity or completeness.
3. At `02:00:00Z`, record A1 as RELEVANT or NOT_RELEVANT with rationale and selected evidence revision 1. These are local screening assertions. UNASSESSED is retained when applicability is unknown; screening without pinned evidence is counted explicitly.
4. Record `SYN-CANDIDATE-001` with a fictional reference label, proposed scope and optional supplied source date. Applicability always remains UNASSESSED. References are not fetched or treated as controlling authority. Use a new candidate ID for a changed candidate reference.
5. At `03:00:00Z`, open `SYN-QUESTION-001`, with a question, alternative explanation, limitations and optional evidence pins. Initial status is OPEN. A question is not a finding about an institution or person.
6. At `04:00:00Z`, record a local response with at least one pinned snapshot. RESPONSE_RECORDED means a response is on record, not that rights were satisfied, a concern was resolved or qualified legal review occurred.
7. At `05:00:00Z`, append revision 2 under the same evidence ID. Prior text/hashes remain intact. Questions and domain screenings still pinned to revision 1 now show STALE EVIDENCE and need reassessment. Earlier historical cutoffs do not use this future revision.
8. At `06:00:00Z`, record a new local response pinned to revision 2; at `07:00:00Z`, update the screening with its own revision-2 pins. At `08:00:00Z`, record OPEN with new challenge rationale to reopen the question. The original question clock is retained.
9. Download the blocked Layer A draft and companion bundle. Both snapshot versions resolve through manifest IDs such as `SYN-EVIDENCE-001@1`. The draft remains LEGAL_REVIEW_REQUIRED even if all seven domains are locally screened and all questions have current evidence responses.

Use full RFC3339 UTC/offset timestamps. Activity within a review case is nondecreasing across evidence, screening, candidate and question/response records. Expected case versions reject stale edits, including responses based on a case changed by a source update. Evidence pins must match an existing ID, revision and content hash; duplicates, missing snapshots, wrong hashes and invalid types are rejected. Hashes detect content identity, not authorship, truth, legal sufficiency or applicability.

## Layer A bridge and permanent holds

The draft uses [schema version 0.1.0](../vendor/layer-a/review-record.schema.json). It contains fictional proposal/institution/jurisdiction labels, unresolved qualified-review questions, jurisdictional limitations and execution-authorization conditions. It always exports:

- `review_status: LEGAL_REVIEW_REQUIRED`;
- an unassigned qualified-review role;
- no invented `reviewer_id` or `reviewed_at`;
- an empty `legal_authorities` array, because candidate applicability is unassessed;
- nonempty unresolved questions, conditions and jurisdictional limitations.

The companion bundle retains candidate references, full histories, exact snapshot content, hashes and origin assertions. Evidence IDs in the Layer A record resolve to its manifest; they do not imply that the evidence supports a legal conclusion. All local questions remain represented as awaiting qualified assessment in the draft, including those with recorded responses. Case revision numbers increase with activity; prior snapshots and histories are not erased to clear a gate.

Tests validate the draft against the vendored contract and run the repository's Layer A validator with `--require-ready`; expected exit is 2 with BLOCKED. Structural validity is intake compatibility, not legal sufficiency. No path in this application promotes the record to READY_FOR_HUMAN_DECISION or authorizes implementation. Actual qualified review must use a separately established process.

## Measures and interpretation

| Measure | Definition and limit |
| --- | --- |
| Current recorded domain screenings | Latest RELEVANT/NOT_RELEVANT assertion per A1–A7 domain with no stale pins; a coverage count, not a rights or applicability determination |
| Unassessed/stale domains | Latest UNASSESSED assertions or dependencies pinned to older snapshot revisions |
| Screenings without evidence | Non-UNASSESSED screening assertions with no pinned snapshot; prevents interpreting metadata coverage as evidenced sufficiency |
| Open/stale questions | Latest OPEN questions or local responses whose evidence dependencies are stale |
| Current-evidence responses | RESPONSE_RECORDED with current snapshot references; not legal approval, satisfied rights or resolved concerns |
| Unanswered age | Original question time to cutoff for open/stale questions; separately censored |
| Local response time | Original question to latest current-evidence response timestamp; medians and nearest-rank P90 are descriptive synthetic measures |
| Reopened questions | Transitions from RESPONSE_RECORDED back to OPEN; local challenge history, not an adjudication rate |
| Candidate dates | Supplied dates or explicit unknowns; neither freshness nor controlling authority is independently checked |
| Qualified legal reviews | Always zero in this prototype; coverage and source linkage never change the export hold |

Report cutoffs select visible screening/source/response revisions first; jurisdiction filters use exact fictional labels. Editor views show current full history, while the report can use an earlier cutoff. A new snapshot revision marks older dependencies stale even if the operator repeats identical text; reassessment is explicit. Old revisions remain available as historical evidence. Empty timing samples remain null with explicit sample sizes. No causal claim, rights ranking, institutional legality score or individual allegation is generated.

## Privacy and operating boundary

Use invented identifiers and fictional, non-identifying text only. The model has no individual identity fields or actual protected case-file upload. Free text is not a redaction or anonymization system. Candidate references are recorded labels, not automatically retrieved legal material. Role names are local assertions, not authenticated qualifications. No actual legal advice, rights adjudication, authority acceptance, challenge submission or institutional outreach is provided or performed.

## Interfaces and persistence

- `GET /api/rights` returns review cases and full current histories.
- `POST /api/rights/cases` creates fictional intake.
- `POST /api/rights/cases/{id}/evidence` appends a full-text snapshot revision.
- `POST /api/rights/cases/{id}/screenings` appends a domain-screening assertion with optional pins.
- `POST /api/rights/cases/{id}/authorities` records an unassessed candidate.
- `POST /api/rights/cases/{id}/questions` opens a question with alternatives/limitations.
- `POST /api/rights/cases/{id}/questions/{question_id}/events` records OPEN or RESPONSE_RECORDED with evidence.
- `GET /api/rights/cases/{id}/layer-a` returns the permanently blocked schema-compatible draft.
- `GET /api/rights/cases/{id}/bundle` returns the draft, companion manifest, candidate references and histories.
- `GET /api/rights/report?as_of=...&jurisdiction=...` computes coverage and unresolved-age diagnostics.

Routes share the loopback-only server, host/origin checks and local mutation token. Full workspace JSON export and SQLite backup preserve evidence content, pins and audit/history records. See [backup/restore](APPLICATION.md#export-backup-and-restore). Exported content is local scenario data and should remain outside public git commits.

## Outstanding acceptance

Import and review the full project source; confirm actual scope, applicable jurisdictions/authority, qualified reviewer responsibilities, lawful evidence handling, challenge/correction routes and authenticated provenance. Do not infer actual legal applicability or institutional acceptance from the prototype. Project 016 is not marked complete; the original Layer A assurance rules and pinned synthetic packet remain unchanged.
