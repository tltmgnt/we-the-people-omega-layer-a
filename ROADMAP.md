# Layer A roadmap

This roadmap describes proposed milestones, not a delivery-date commitment or a finding of
legal readiness. Repository release versions and JSON schema versions are separate.

## 0.2.0-alpha — reproducible review foundation

Goal: a contributor can understand the seven-domain framework, validate a review packet,
reproduce a blocked pilot and inspect a versioned cross-layer exchange locally.

| Deliverable | Acceptance evidence |
| --- | --- |
| Project overview and accurate inventory | README links to delivered artifacts; changelog distinguishes initial and unreleased work |
| Review contract and gate | Schema 0.1.0, validator, documented roles/statuses/escalation, required-field and readiness tests |
| Synthetic pilot | Preserved intake and escalation revisions, source manifest, reproducible blocked outcome |
| Seven domains | A1–A7 questions, evidence requests, escalation triggers and shared recording guidance |
| Proposed cross-layer contract | Schema 0.1.0, B/C/D synthetic metadata, pinned A review and evidence manifest, negative consistency tests |
| Release preparation | This roadmap and the [release criteria](Docs/Releases/0.2.0-alpha.md), reviewed on the final main commit |

Implementation is present on the staged PR chain as of 2026-10-31, not yet on main.
This is a historical preparation snapshot; use live PRs and final-commit checks for current status.
Domain content is proposed guidance awaiting qualified review. No operational deployment,
legal certification or completed jurisdiction-specific legal pilot is included.

## 0.3.0-alpha — reviewed pilot and stronger review history

Proposed next scope, subject to maintainer and reviewer agreement:

- Select one actual program and jurisdiction with an accountable institution and qualified,
  authorized legal reviewer. Define the question, data boundaries and source plan before
  collecting case material.
- Assess relevant dated authorities and all seven domains; record applicability, alternative
  interpretations, uncertainty, reviewer attribution and a versioned outcome. A properly
  justified blocked outcome is acceptable; readiness is not a target to optimize for.
- Define and validate historical revision and transition rules, including challenges,
  changed authority and correction handling. Preserve prior records.
- Review the initial schema and checklist usability against the pilot findings. Propose
  incompatible changes under a new schema version rather than silently reinterpreting 0.1.0.

Exit evidence: an appropriately shareable, qualified human-reviewed packet, documented
history rules and tests, and maintainer disposition of pilot findings. Owner assignments,
program, jurisdiction and dates are not yet agreed.

## Subsequent integration milestone

Before claiming production or cross-repository integration:

- Agree contracts and change review with affected B/C/D maintainers.
- Define authoritative repository/ref selection, authenticated provenance, permissions,
  freshness/revocation policy and unavailable-source handling.
- Exercise updates, stale references, disputed findings and rollback using non-sensitive data.
- Identify accountable institutional decision makers and separately verify required authority.

Exit evidence: reviewed agreements, reproducible integration checks and documented operational
responsibilities. The current local exchange does not satisfy these conditions.

## Decisions and ownership

| Decision | Proposed accountable role | Status |
| --- | --- | --- |
| Release scope and final approval | Repository maintainer | Pending |
| License for code/docs and third-party treatment | Project owner | Pending; see license-selection note |
| Domain guidance review | Qualified domain reviewers selected by maintainer | Unassigned |
| Jurisdiction-specific pilot and legal reviewer | Participating institution and authorized reviewer | Unassigned |
| External contract adoption | Affected layer maintainers | Not agreed |

These are required roles, not assignments to named people. Do not treat an unassigned
reviewer or an unresolved decision as completed work. Follow the
[release procedure](Docs/Releases/0.2.0-alpha.md) for the first alpha milestone.
