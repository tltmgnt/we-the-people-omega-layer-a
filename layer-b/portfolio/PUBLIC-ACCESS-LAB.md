# Project 014 — synthetic records, complaints and meetings

## Delivered scope

The local application tracks fictional records requests and complaints, receipt/handoff/closure/reopening history, external deadline assertions, versioned response-scope records and checks. It also tracks fictional meeting schedules, revised notice/publication references, participation-access assertions and notice checks. This prototype follows the [editorial plan](plans/014.md), not the unread linked source. It does not calculate legal deadlines, apply exemptions, determine compliance or publish/disclose material.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/public-access>. Restart an existing server to add the routes/tables. Existing workspace records remain intact. No requests, responses, notices or measurements are inserted automatically.

## Fictional response walkthrough

1. Enter an operator identifier. Receive `SYN-RECORDS-001`, kind RECORDS_REQUEST, area `Demo area`, receipt `2026-01-01T00:00:00Z`, with externally stated due time `06:00:00Z` and scenario evidence. A COMPLAINT uses the same workflow. Leave the due field blank when it is unknown; no deadline is inferred.
2. Record a PARTIAL response, fictional sent and record times `04:00:00Z`, with reference labels, scope evidence and any fictional review-route/restriction references. Verify at `05:00:00Z` using a distinct identifier. A passing check of a partial assertion does not make it complete; closure is rejected.
3. Record a COMPLETE response at sent/record time `07:00:00Z`, then verify at `08:00:00Z`. Completeness means the scenario's declared scope, not a legal determination that every record must be disclosed. Close at `08:30:00Z` with evidence.
4. Record a new external due-date assertion at `09:00:00Z`, due `10:00:00Z`. The earlier response remains late against its captured six-hour assertion. Each response pins the already recorded deadline assertion applicable at its fictional sent time, so a later assertion cannot rewrite that comparison, even when simulated timestamps tie.
5. Reopen at `09:00:00Z`. The previous checked response cannot close the new open cycle. Record a handoff at `09:30:00Z`, a fresh COMPLETE response at `10:00:00Z`, a check at `11:00:00Z`, and closure at `11:30:00Z`. The new response meets the now-recorded due time, but total elapsed response time remains ten hours from original receipt. Reopening and handoffs do not reset the clock.

All times above are on `2026-01-01` and must be entered as full RFC3339 UTC/offset timestamps. Record/revision times must be nondecreasing across lifecycle, deadline, response and check histories. Fictional sent time cannot follow record time or precede receipt/current reopening. Expected versions reject stale writes. A revised response or a reopened cycle requires fresh evidence; a distinct verifier identifier is a separation rule, not authenticated independent review.

## Fictional meeting walkthrough

1. Schedule `SYN-MEETING-001`, title `Fictional public meeting`, area `Demo area`, registered `2026-01-01T00:00:00Z`, start `2026-01-02T12:00:00Z`.
2. Record fictional notice publication and record times `2026-01-01T12:00:00Z`, participation access INCOMPLETE or UNKNOWN, and evidence. Verify at `13:00:00Z`. Lead time is 24 hours, while missing/unknown participation and agenda evidence remain visible.
3. With the supplied threshold blank, no threshold rate or count is assessed. Enter 24 hours only as an explicit scenario comparison; it is not an official notice requirement.
4. Revise the notice at `14:00:00Z` to fictional publication `11:00:00Z`, access AVAILABLE, with fictional participation and agenda reference labels. The earlier check is stale until a fresh check at `15:00:00Z`. The current checked lead time is 25 hours. AVAILABLE requires a participation reference, but neither that label nor a check proves accessible participation or compliance.

Notice publication can be recorded after the meeting starts; negative lead times are retained rather than rejected or hidden. Record/revision time is separate from fictional publication time, allowing correction of an earlier publication assertion while preserving revision order. The latest check is bound to the exact notice revision. No notice is actually published and no participant is contacted.

## Measures and safeguards

| Measure | Definition and limitation |
| --- | --- |
| Latest complete response hours | Original receipt to fictional sent time of the latest checked COMPLETE response in the current open cycle; not a legal compliance or satisfaction result |
| Unresolved age | Original receipt to cutoff for open cases without a current checked complete response; handoffs and reopenings do not reset age |
| Incomplete/unverified responses | Latest PARTIAL/UNKNOWN scope and missing/failed current checks counted separately; quick partial replies never enter complete-response timing |
| Recorded due comparison | Current checked complete response compared with its captured, immutable external deadline assertion that existed at fictional sent time; unknown assertions stay unassessed |
| Overdue unresolved cases | Open unresolved cases whose current recorded due time is before cutoff; a recorded-date diagnostic, not a statutory violation finding |
| Review-route references | Missing reference labels remain explicit; their presence does not prove adequate review rights or that a request was sent |
| Meeting lead | Scheduled start minus fictional publication time of the latest checked notice, in UTC calendar hours; negative values preserved |
| Notice threshold | No default. Rate/count assessed only when a finite nonnegative scenario threshold is supplied and checked notices exist |
| Participation access | AVAILABLE versus INCOMPLETE/UNKNOWN assertions and missing agenda labels; these are evidence gaps, not certifications |

Historical cutoff selects visible revisions/checks before measurement. Area filters apply to cases and meetings; case-kind filters apply only to records/complaint cases. Registered future meetings can have notices assessed before their start. Medians and nearest-rank P90 are descriptive synthetic statistics with explicit sample sizes; empty samples remain null. No working-day, holiday, pause, extension, legal-duty, exemption-validity, disclosure or retention rule is inferred.

## Privacy and operating boundary

Use only invented `SYN-` identifiers and fictional reference labels. The structured model has no requester name, address, contact fields, protected document body or actual notice upload. Free text is not a redaction system. Restriction, scope and review-route references preserve unresolved questions; they do not decide exemption applicability or legal rights. No actual request, response, publication, file deletion, retention change or outreach occurs. Qualified source and jurisdiction review remain necessary.

## Interfaces and persistence

- `GET /api/public-access` returns fictional cases and meetings.
- `POST /api/public-access/cases` records receipt.
- `POST /api/public-access/cases/{id}/deadlines` records an external due-date assertion.
- `POST /api/public-access/cases/{id}/responses` records/revises response scope and captures the applicable prior deadline assertion.
- `POST /api/public-access/cases/{id}/checks` checks the current response.
- `POST /api/public-access/cases/{id}/events` records HANDOFF, CLOSED or REOPENED.
- `POST /api/public-access/meetings` schedules a fictional meeting.
- `POST /api/public-access/meetings/{id}/notices` records/revises a fictional notice.
- `POST /api/public-access/meetings/{id}/checks` checks its current revision.
- `GET /api/public-access/report?as_of=...&area=...&kind=...&min_notice_hours=...` computes reports; omit optional filters/threshold when unknown.

These routes share the loopback-only server, host/origin protections and local mutation token. Full JSON export and SQLite backup preserve histories, assertions, checks and audit entries. See [backup/restore](APPLICATION.md#export-backup-and-restore).

## Outstanding acceptance

Import and review the full source; confirm jurisdiction, responsible owners, actual deadlines, response scope, legal review routes, exemptions, retention/access requirements and accessible participation practices. Qualified acceptance and institutional authorization remain separate. This prototype does not mark project 014 complete or change the original Layer A hold and pinned packet.
