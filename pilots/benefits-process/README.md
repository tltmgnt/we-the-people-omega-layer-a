# Hypothetical benefits-process pilot

This reproducible walkthrough exercises intake, evidence references, revision preservation
and escalation. All actors and proposal details are synthetic. No human legal review has
occurred; the recorded outcome is a hold pending that review.

## Synthetic proposal

A hypothetical public agency proposes changing a digital benefits process to route
applications through an online form and send status notices electronically. The benefits
program, governing jurisdiction, institutional authority, accessibility requirements and
appeal procedures have not been specified. The pilot makes no finding about what law applies.

Potential questions for review include access for people unable to use the digital route,
notice delivery, opportunities to correct errors and appeal, privacy, and institutional
authority. These are research prompts, not findings that any particular right or rule applies.
Tribal jurisdiction and government-to-government implications must be assessed if relevant;
the unspecified jurisdiction does not permit an assumption that they are inapplicable.

## Review packet

| Artifact | Purpose |
| --- | --- |
| [01-intake.json](01-intake.json) | Revision 1: DRAFT, with incomplete authority and unresolved questions |
| [02-escalated.json](02-escalated.json) | Revision 2: LEGAL_REVIEW_REQUIRED, preserving the same review and proposal identifiers |
| [sources.json](sources.json) | Resolves synthetic evidence IDs to sections of this document; explicitly contains no legal sources |

The proposal is derived from the [original example](../../example-review.json).
Synthetic evidence documents the proposal and triage only. Populating evidence_ids does not
resolve missing legal authority or establish sufficiency. Source dates are fixture preparation
dates, not dates of law or dates of completed legal review.

## Triage and recorded outcome

1. Intake captures the proposal and unknown jurisdiction as revision 1.
2. Triage identifies missing governing law, reviewer assignment and verified notice/appeal
   procedures. The original unresolved questions, limitations and hold condition are preserved.
3. The packet is marked LEGAL_REVIEW_REQUIRED in revision 2 and includes a reference to this
   triage explanation. This is a simulated submission state, not a message sent to a reviewer.
4. The validator accepts both records structurally and reports BLOCKED. The readiness check
   returns exit 2 for both. Replacing the revision 2 status with READY_FOR_HUMAN_DECISION
   fails schema validation because attribution, authority and unresolved blockers remain missing.

No reviewer_id or reviewed_at is asserted: no person has supplied a legal assessment.
An authorized institution must identify the program and jurisdictions, assign a qualified
authorized legal reviewer, collect applicable dated sources and evidence, and resolve or
document the outstanding questions before any later readiness determination.

| Responsibility | Current state |
| --- | --- |
| Proposal author/institution | Synthetic and unspecified |
| Qualified authorized legal reviewer | Unassigned; review pending |
| Authorized institutional decision maker | Unidentified; no decision recorded |
| Implementation | Blocked |

Preserve both snapshots. A subsequent substantive review must retain review_id, increment
revision, identify the actual human reviewer and document reasons and sources. Challenges,
new facts or changed authority require reassessment under the
[assurance workflow](../../Docs/Assurance/review-gate.md).

## Reproduce

From the repository root after installing requirements-dev.txt:

```sh
python -m unittest discover -s tests -v
python scripts/validate_review.py pilots/benefits-process/01-intake.json pilots/benefits-process/02-escalated.json
python scripts/validate_review.py --require-ready pilots/benefits-process/01-intake.json pilots/benefits-process/02-escalated.json
```

Expected exit codes: tests 0, structural validation 0, readiness 2. Tests also check stable
identifiers, consecutive fixture revisions, resolvable synthetic evidence and resistance to
a status-only readiness change. These fixture checks do not implement general historical
transition enforcement.

## Pilot boundary

This walkthrough completes the synthetic intake-to-escalation exercise. A jurisdiction-specific
pilot with real source assessment, qualified human legal review and a reviewed institutional
outcome remains future work.
