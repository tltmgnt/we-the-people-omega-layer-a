# Layer A domain checklists

These seven checklists organize a proposed review process. They ask what must be investigated;
they do not declare which law applies or decide whether an action is lawful. Checklist
completion neither changes the review status automatically nor authorizes implementation.

## Domains

| Domain | Focus |
| --- | --- |
| [A1 Rights and Liberties](A1-rights-and-liberties.md) | Potential effects on people’s rights, protected interests and practical access to public processes. |
| [A2 Rule of Law](A2-rule-of-law.md) | The authority, reasons, consistency and challengeability of a proposed institutional action. |
| [A3 Elections and Representation](A3-elections-and-representation.md) | Potential effects on election administration, participation and representative processes. |
| [A4 Courts and Justice](A4-courts-and-justice.md) | Potential effects on adjudication, court access and review or remedy mechanisms. |
| [A5 Ethics and Integrity](A5-ethics-and-integrity.md) | Conflicts, influence, stewardship and accountability in the proposed institutional process. |
| [A6 Federalism](A6-federalism.md) | Authority and responsibility across federal, state and local institutions, with a separate Tribal-sovereignty review. |
| [A7 Tribal Sovereignty](A7-tribal-sovereignty.md) | Distinct Tribal authority, affected Tribal Nations and government-to-government relationships; assess separately from state/local government. |

## Shared recording instructions

1. Screen all seven domains against the defined proposal, actor, jurisdiction, date and scope.
   Mark each domain relevant, potentially relevant or not applicable in accompanying review
   materials. Give reasons for not applicable; uncertainty is not a reason to omit a domain.
2. For each relevant question record the facts, proposed interpretation, dated source
   references, source applicability, reviewer role, uncertainty and any required follow-up.
   Distinguish binding law, interpretation and proposed project standards. Do not collect
   confidential case materials or sensitive personal data in this repository.
3. Request the evidence described by the domain; record gaps explicitly. Identify the
   responsible human reviewer and action owner. General reference sites are starting
   points, not substitutes for applicable statutes, decisions, treaties or Tribal law.
4. Escalate unresolved authority, rights, procedure or jurisdiction questions to qualified,
   authorized human legal review. Keep the packet blocked using the
   [assurance workflow](../Assurance/review-gate.md).
5. Preserve findings and challenges by review_id and revision. Do not remove unresolved
   issues merely to obtain a ready status.

A reusable entry in accompanying review materials:

| Item | Record |
| --- | --- |
| Domain/question | Domain ID and the specific question assessed |
| Relevance and reasons | Relevant / potentially relevant / not applicable, with explanation |
| Facts and scope | Actor, action, jurisdiction, date and affected interests |
| Sources | Stable references, source dates, applicability and authority type |
| Assessment | Findings, competing interpretations and remaining uncertainty |
| Responsibility | Actual reviewer role/identity when assigned; action owner and follow-up |
| Outcome | Blockers, escalation and references to the versioned review record |

This is a documentation template, not a new JSON record type.

## Mapping to the review record

Use the existing [schema 0.1.0](../../schemas/review-record.schema.json).
Keep detailed domain assessments in accompanying materials; do not add unsupported JSON fields.

| Domain assessment content | Existing record field |
| --- | --- |
| Proposal, actor and jurisdiction | proposal_id, proposal_summary, responsible_institution, jurisdictions |
| Applicable authority references | legal_authorities |
| Potential rights and affected interests | rights_affected |
| Required process and review routes | procedural_requirements, accountability_mechanisms |
| Unresolved jurisdiction or authority boundaries | jurisdictional_limitations |
| Open legal questions and blocking follow-up | unresolved_questions, conditions |
| Supporting assessment and source references | evidence_ids |
| Review state and revision | review_status, reviewer_role, revision |
| Attribution after actual review | reviewer_id, reviewed_at, as applicable |

The schema does not validate domain coverage, source accuracy or reviewer qualifications.
Readiness remains subject to the assurance gate's empty-blocker and attribution requirements.
When a field calls for an assessment but nothing is identified, record a reasoned explanation
rather than an empty placeholder; do not imply that an unexamined issue was cleared.

## Applying the checklists to the synthetic pilot

For the [benefits-process pilot](../../pilots/benefits-process/README.md), A1 access and
procedure, A2 institutional authority and A4 review routes are potential concerns.
A5 interests and oversight, A6 jurisdiction and A7 Tribal implications require screening;
the unspecified institution and jurisdiction cannot clear them. A3 has no identified
election function in the synthetic proposal, but that conclusion needs reassessment if
scope changes. These are suggested triage notes, not completed legal assessments.
The pilot remains LEGAL_REVIEW_REQUIRED.

## Official reference starting points

- [National Archives Constitution transcription](https://www.archives.gov/founding-docs/constitution-transcript):
  foundational text with links indicating subsequent amendments.
- [U.S. Election Assistance Commission](https://www.eac.gov/):
  election-administration resources; identify the applicable state/local authorities separately.
- [Indian Affairs Tribal consultations](https://www.bia.gov/service/tribal-consultations):
  federal consultation resources; consult the relevant Tribal authorities and context-specific requirements.

Reference pages accessed 2026-10-31. Their inclusion is not a finding of governing authority.
Domain-specific source research, qualified human review, and operational implementation
remain future work.
