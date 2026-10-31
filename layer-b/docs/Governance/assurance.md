# Governance and operational assurance

## Responsibility

| Level | Responsibility |
| --- | --- |
| Operational owner | Process, service standards, resources and day-to-day correction |
| Assurance owner | Independent checks, evidence quality, control effectiveness and escalation |
| Public accountability | Lawful transparency, oversight, complaints and documented remedies |

For multi-institution work document responsibilities, funding, information-sharing authority,
records ownership, escalation and disputes. Coordination does not erase each participant's
independent obligations. Missing owners remain explicit gaps.

## Record and workflow

Use [operational-review schema 0.1.0](../../schemas/operational-review.schema.json).

| Status | Meaning |
| --- | --- |
| DRAFT | Bounded proposal and evidence intake |
| ANALYSIS_REQUIRED | Operational diagnosis or verification remains incomplete |
| LEGAL_REVIEW_REQUIRED | Layer A authority/rights/jurisdiction questions remain unresolved |
| READY_FOR_HUMAN_DECISION | Packet is ready for a separately authorized human decision, not execution |

An author may submit a draft for analysis or legal review. A qualified legal reviewer
handles legal findings; an operational and assurance reviewer assess operational findings.
Record actual attribution when it occurs. A ready packet returns to analysis or legal review
when scope, authority, evidence or unresolved challenges change. Preserve record_id, increment
revision and retain prior versions. The validator checks snapshots, not historical transitions.

The draft schema requires owners, six-domain screening, lifecycle stage, Layer A reference,
evidence entries, metrics, gaps, uncertainty and revision. Screening is RELEVANT,
POTENTIALLY_RELEVANT or NOT_APPLICABLE with reasons. Detailed assessments remain accompanying
materials. A READY_FOR_HUMAN_DECISION record requires reviewer_id, reviewed_at,
no unresolved_questions and no unresolved gaps. Its pinned Layer A record must also be
READY_FOR_HUMAN_DECISION. Attribution and evidence sufficiency are assertions requiring
human verification; software cannot authenticate them.

## Validation behavior

The consumer rejects duplicate JSON keys at any depth, NaN/Infinity constants, invalid
types/versions, unknown/missing evidence IDs, changed exact-byte hashes, mismatched proposal
or review identities and paths outside the repository. It validates the pinned Layer A
snapshot against the unchanged upstream Layer A schema. References are local fixture paths;
no remote fetch or authenticated approval is performed.

Exit 0 means structurally consistent, not permission. --require-ready exits 2 when held.
Invalid/unreadable input exits 1. Readiness still means human decision only.
The permit example must remain held while authority and operational questions are unresolved.

## Consequential action boundary

Financial commitments, hiring/discipline, vendor eligibility, record disclosure and service
denials need their separately applicable authority, safeguards and human decisions.
No autonomous action is implemented. Before live pilots, define access controls, privacy,
records retention, security, incident handling, rollback and authorized decision roles.
