# Constitutional Legitimacy Assurance Gate

This is a proposed repository review workflow. It records human review and outstanding
questions; neither a valid JSON record nor a ready status certifies legality or authorizes implementation.

## Record contract

Use [schema version 0.1.0](../../schemas/review-record.schema.json) and the
[synthetic example](../../example-review.json). Required fields describe the proposal,
institution, jurisdictions, authority, rights, procedures, limitations, accountability,
unresolved questions, status, reviewer role, conditions, evidence references and revision.
Use stable review, proposal and evidence identifiers across layers.
Source references must resolve in the accompanying review materials and include source
dates and applicability; the validator checks strings, not the truth or sufficiency of sources.
Empty authority and evidence arrays are permitted during intake so uncertainty is explicit.
Unknown fields, blank strings, invalid types and unsupported versions or statuses fail validation.

All entries in unresolved_questions, conditions and jurisdictional_limitations are
treated as blockers for readiness. Record resolved matters and nonblocking scope
explanations in accompanying review materials. Do not erase unresolved issues to pass validation.
READY_FOR_HUMAN_DECISION additionally requires nonempty authority and evidence references,
reviewer_id and an RFC 3339 reviewed_at timestamp. These are recorded assertions;
software does not verify reviewer identity, qualifications or jurisdictional authority.

## Responsibilities and transitions

| Status | Meaning and next step | Responsible actor |
| --- | --- | --- |
| DRAFT | Intake; move to LEGAL_REVIEW_REQUIRED when submitted or uncertainty is identified. | Proposal author |
| LEGAL_REVIEW_REQUIRED | Hold for qualified, authorized human legal review; move to CHANGES_REQUIRED, REJECTED or READY_FOR_HUMAN_DECISION after review. | Human legal reviewer |
| CHANGES_REQUIRED | Hold while changes or evidence are outstanding; resubmit as LEGAL_REVIEW_REQUIRED. | Author revises; reviewer reassesses |
| READY_FOR_HUMAN_DECISION | Review packet is ready for the separately authorized actor's decision; no implementation permission is conveyed. | Human legal reviewer records readiness |
| REJECTED | Proposal cannot advance in its reviewed form; a substantive revision returns to DRAFT. | Human legal reviewer records reasons |

Any new challenge, changed authority, material proposal change, or discovered uncertainty
returns a ready packet to LEGAL_REVIEW_REQUIRED. Serious unresolved questions must be
escalated to a qualified human legal reviewer and remain blocked.
Record the actual reviewer's role and identifier when a review occurs; a placeholder role
in the example is a request for review, not evidence that review happened.

For every change retain review_id, increment revision, and preserve the previous record
in version control. Record reasons, sources, challenges, corrections and human attribution
in the associated review materials. Re-review changed scope and jurisdiction, including
Tribal authority where applicable. The status table is a human workflow: this initial
validator checks individual snapshots, not historical transitions or revision monotonicity.

## Running checks

From the repository root, with Python 3.12:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/validate_review.py example-review.json
python scripts/validate_review.py --require-ready example-review.json
```

The first validation exits 0 and prints VALID; BLOCKED. The readiness check exits 2
because the example requires legal review. Exit 1 means malformed, unreadable or
schema-invalid input; with multiple inputs it takes precedence over exit 2.
Even exit 0 with --require-ready means readiness for human decision only.
CI checks structure and tests; passing CI is never an approval gate for implementation.

## Synthetic pilot

The [benefits-process walkthrough](../../pilots/benefits-process/README.md) preserves
intake and escalation revisions, resolves synthetic evidence references and reproduces a
blocked outcome. No qualified human legal review has occurred. A jurisdiction-specific
pilot with applicable legal sources, human review and institutional outcome remains
future work, along with domain-specific legal guidance.
