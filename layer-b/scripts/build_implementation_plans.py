"""Build proposed plans from supplied titles and explicit editorial profiles.

These are draft requirements, not transcriptions of unread source documents.
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def build():
    register = json.loads((ROOT / 'portfolio/project-register.json').read_text())
    profiles = {}
    for line in (ROOT / 'portfolio/proposed-profiles.txt').read_text().splitlines():
        identifier, outcome, records, metric, safeguard = line.split('|')
        profiles[identifier] = dict(outcome=outcome, records=records, metric=metric, safeguard=safeguard)
    plans = {}
    for p in register['projects']:
        identifier = p['project_id']
        profile = profiles.get(identifier, dict(
            outcome='Confirm the original project title, purpose and boundaries before selecting an implementation.',
            records='Unassigned foundational documents; exact project-to-source mapping remains unresolved.',
            metric='Choose a measurable public purpose and counter-metric after confirming this project definition.',
            safeguard='Do not infer a project identity or assign a foundational source without owner confirmation.'))
        steps = [
            ('source', 'Import and review requirements', 'Import the complete source text with origin, content hash and reviewer record.', 'Current source content is readable, provenance is recorded, and requirements and missing sections are documented.'),
            ('scope', 'Confirm scope and accountability', f"Define one bounded use case: {profile['outcome']}", 'Owner, affected users, jurisdiction, exclusions, user actions and acceptance criteria are recorded; scope is checked against the source.'),
            ('data', 'Define the input contract', f"Specify fields, identifiers, provenance and quality rules for: {profile['records']}", 'Document valid and invalid example records, access and retention limits, missing-value handling and source freshness.'),
            ('baseline', 'Establish baseline and safeguards', profile['metric'], 'Baseline and counter-metric definitions include units, denominator, time window, missingness and uncertainty; unknown values remain null.'),
            ('build', 'Implement the bounded workflow', f"Deliver an executable workflow for the confirmed use case. Apply: {profile['safeguard']}", 'Users can complete the documented use case with persisted records, input validation, error handling, accessible interactions and traceable corrections.'),
            ('test', 'Verify behavior and failure paths', 'Test the agreed workflow using authorized examples or explicitly labeled synthetic fixtures.', 'Record reproducible test commands and results covering the main workflow, malformed input, missing evidence, source changes and recovery; verify the counter-metric.'),
            ('review', 'Record independent acceptance and limitations', 'Have qualified reviewers compare the delivered workflow with the confirmed requirements.', 'Record reviewer identity, evidence references, unresolved findings, limitations and a support/maintenance owner. Software completion does not authorize live government action.'),
            ('handoff', 'Prepare reproducible handoff', 'Document setup, dependency versions, backup/restore, operating boundaries and rollback.', 'A second person can reproduce the accepted workflow and restore a workspace from a tested backup. Any live deployment decision is separately documented.')
        ]
        plans[identifier] = {'basis': 'EDITORIAL DRAFT from registered title; linked source content has not been reviewed. Confirm or replace after source import.', **profile,
            'steps': [dict(id=i, title=t, deliverable=d, acceptance=a) for i,t,d,a in steps]}
    plans['023']['basis'] = 'User-supplied full specification available in portfolio/sources/023-user-specification.md (2026-10-31); source wording is Markdown-normalized. Linked Google Doc identity and external claims are not independently verified. See JUSTICE-LAB.md for implementation traceability and outstanding institutional acceptance.'
    return register, plans


def main():
    register, plans = build()
    directory = ROOT / 'portfolio/plans'
    directory.mkdir(exist_ok=True)
    index = ['# Project implementation plans', '', 'All plans are editorial proposals pending confirmation against full source documents. These files do not represent completed project implementations.', '', '| ID | Project |', '| --- | --- |']
    for p in register['projects']:
        identifier, plan = p['project_id'], plans[p['project_id']]
        title = p['title'] or 'Title and scope to confirm'
        index.append(f"| {identifier} | [{title}]({identifier}.md) |")
        lines = [f'# {identifier} — {title}', '', plan['basis'], '', '## Proposed outcome', '', plan['outcome'], '', '## Input records', '', plan['records'], '', '## Measurement and counter-metric', '', plan['metric'], '', '## Safeguard', '', plan['safeguard'], '', '## Implementation and acceptance', '']
        for step in plan['steps']:
            lines += [f"### {step['title']}", '', step['deliverable'], '', '**Acceptance:** '+step['acceptance'], '']
        state = 'Proposed plan only. No source import, project-specific executable workflow, completed tests, reviewer approval or institutional adoption is claimed.'
        if identifier == '009':
            state = 'A [synthetic permit lifecycle and measurement prototype](../PERMIT-LAB.md) is implemented with automated tests. It is based on the supplied starter scenario. The linked full source document, real program scope, qualified acceptance and live institutional adoption remain outstanding; this project is not marked complete.'
        if identifier == '010':
            state = 'A [synthetic asset-maintenance and verification prototype](../MAINTENANCE-LAB.md) is implemented with automated tests based on the proposed plan and Layer B public-works prompts. The linked source document remains unread. Actual process rules, safety controls, qualified acceptance and institutional adoption are outstanding; this project is not marked complete.'
        if identifier == '011':
            state = 'A [synthetic sanitation-service prototype](../SANITATION-LAB.md) is implemented with automated tests based on the proposed plan. It records aggregate route runs, verification, recovery and anonymous service-report histories. The linked source remains unread; actual requirements, qualified acceptance and institutional adoption are outstanding. This project is not marked complete.'
        if identifier == '012':
            state = 'A [synthetic transit reliability/accessibility prototype](../TRANSIT-LAB.md) is implemented with automated tests based on the proposed plan. It records scheduled arrival boundaries, verified outcomes, measured aggregate passenger delay and separate accessibility findings. The linked source remains unread; actual requirements, qualified acceptance and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '013':
            state = 'A [synthetic housing referral/follow-up prototype](../HOUSING-LAB.md) is implemented with automated tests based on the proposed plan. It records consent assertions, referral/handoff history, event-specific service/follow-up checks, interruptions and review-request responses. The linked source remains unread; actual requirements, qualified acceptance and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '014':
            state = 'A [synthetic records, complaints and meetings prototype](../PUBLIC-ACCESS-LAB.md) is implemented with automated tests based on the proposed plan. It tracks response scope, captured external deadline assertions, handoffs/reopening and checked meeting-notice/access references. The linked source remains unread; actual rules, qualified acceptance and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '015':
            state = 'A [synthetic utilities-continuity prototype](../UTILITIES-LAB.md) is implemented with automated tests based on the proposed plan. It records assets, interruption/work/restoration cycles, scenario-quality checks, escalation-route references and aggregate incident-associated connection-hours. The linked source remains unread; actual rules, safety criteria, qualified acceptance and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '016':
            state = 'A [synthetic rights-evidence and review-intake prototype](../RIGHTS-LAB.md) is implemented with automated tests based on the proposed plan and existing Layer A record contract. It preserves pinned snapshots, A1–A7 screening, unassessed candidate authorities, questions/challenges and permanently blocked Layer A draft exports. The linked source remains unread; actual applicability, qualified review and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '017':
            state = 'A [synthetic election-service administration prototype](../ELECTION-SERVICES-LAB.md) is implemented with automated tests based on the proposed plan. It records scenario readiness, anonymous access observations, revision-specific checks and correction/reopening histories. It does not assess election validity or representation. The linked source remains unread; actual requirements, qualified acceptance and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '018':
            state = 'A [synthetic finance reconciliation prototype](../FINANCE-LAB.md) is implemented with automated tests. It keeps accounting categories distinct, preserves signed entry history and records revision-specific comparison totals, discrepancies and separate outcome notes. The source remains unread; actual accounting requirements, qualified acceptance and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '023':
            state = 'The [Project 023 justice-observatory implementation](../JUSTICE-LAB.md) delivers a synthetic local workspace based on the [user-supplied full specification](../sources/023-user-specification.md): ten dimensions, eight modules, evidence revisions, caseflow/remand/reentry timing, remedy checks, metric contracts, role reviews and pilot phase records. Automated software tests cover the bounded workflow. External data ingestion, qualified legal/practitioner review, institutional deployment and the real 90-day pilot remain outstanding; this is not a claim of institutional project completion.'
        if identifier == '019':
            state = 'A [controllable synthetic procurement/delivery use case](../PROCUREMENT-LAB.md) is implemented with all nine workflow states, separate current-revision acceptance checks, correction loops, cancellation, presets and snapshot restoration. Automated software tests exercise the bounded scenario. The linked full source remains unread; actual contract/competition data, qualified acceptance and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '020':
            state = 'A [controllable synthetic education-service use case](../EDUCATION-LAB.md) is implemented with nine states, access/delivery milestones, interruptions, revision-specific continuity checks by a distinct recorder identifier, withdrawal, presets and snapshot restore. Automated software tests cover the bounded scenario. The linked full source remains unread; actual access/learning measures, protected-data governance, qualified acceptance and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '021':
            state = 'A [controllable synthetic health-service referral use case](../HEALTH-LAB.md) is implemented with eleven states, a fictional consent milestone, referrals/waiting, interruptions, revision-specific continuity checks, decline/withdrawal, presets and snapshot restore. Automated tests cover the bounded administrative scenario. No clinical decisions or health outcomes are assessed. The linked full source remains unread; actual protected-data/consent governance, qualified review and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '022':
            state = 'A [controllable synthetic emergency-readiness exercise](../EMERGENCY-LAB.md) is implemented with eleven states, separate current-revision readiness and correction gates, response/after-action milestones, abort/cancel paths, explicit preset checks and snapshot restore. Automated tests cover the bounded rehearsal. Live dispatch and readiness certification remain false. The linked full source remains unread; actual safety/operating rules, qualified review and institutional adoption remain outstanding. This project is not marked complete.'
        if identifier == '023':
            state += ' The [controllable justice use case](../JUSTICE-CONTROLS.md) adds fifteen isolated scenario states, current notice/remedy/reentry record checks, remand/rehearing loops, both closure paths, presets and snapshot restoration; it makes no judicial or release decisions.'
        lines += ['## Source', '', p['source_url'] or 'No assigned source. Confirm the source and project definition before implementation.', '', '## Current delivery state', '', state, '']
        (directory / f'{identifier}.md').write_text('\n'.join(lines))
    (directory / 'README.md').write_text('\n'.join(index)+'\n')


if __name__ == '__main__':
    main()
