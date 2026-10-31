# Project 013 — synthetic housing-service referral

## Delivered scope

The local application provides fictional intake, consent-assertion history, referrals, accepted handoffs, returned referrals, recorded service starts, follow-up, interruptions, closure states and independent review-request response histories. Service and follow-up assertions can receive event-specific verification records. This prototype follows the [editorial plan](plans/013.md), not the unread linked project source. It does not determine eligibility, approve benefits, establish actual consent or make housing placements.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/housing>. Restart an existing server to add the tables/routes. Prior portfolio and lab records remain intact. No cases, consent claims or measurements are inserted automatically.

## Fictional walkthrough

1. Enter an operator identifier. Create `SYN-HOUSING-001`, program `Demo housing support`, area `Demo area`, intake `2026-01-01T00:00:00Z`, with fictional evidence. An optional fictional external-notice reference is a label only, not a notice upload, eligibility result or legal finding.
2. Attempt REFERRED at `01:00:00Z`. It is blocked until a current RECORDED consent assertion exists. Record that assertion at `01:00:00Z` with scenario evidence. This local assertion does not constitute real consent or authorize outreach.
3. Record REFERRED at `02:00:00Z`, HANDOFF_ACCEPTED at `03:00:00Z`, and SERVICE_STARTED at `04:00:00Z`, with next follow-up due `08:00:00Z`. Each event needs evidence; the recorded start is not yet a verified outcome.
4. Verify the service-start event at `05:00:00Z` using a distinct identifier. At this point, measured referral-to-start time is two calendar hours; continuing service remains unestablished.
5. Record FOLLOW_UP at `06:00:00Z` with CONTINUING or UNKNOWN continuity and next follow-up due `10:00:00Z`. Verify this separate event at `07:00:00Z`. The start's earlier check cannot verify this follow-up.
6. At cutoff `2026-01-01T12:00:00Z`, a checked CONTINUING follow-up is shown separately from the two-hour first-start measure, and the next follow-up is overdue. Missing future follow-up plans are reported separately rather than interpreted as no need.
7. Record WITHDRAWN consent assertion at `07:30:00Z`. Further referral/handoff/start/follow-up actions are blocked. SERVICE_INTERRUPTED at `08:00:00Z` and CLOSED_NO_SERVICE at `08:30:00Z` can still be recorded to preserve the operational history. Historical verified first-start time remains visible, while current interruption and consent-hold counts expose the later gap.
8. Open `SYN-REVIEW-001` at `09:00:00Z`, record RESPONDED at `10:00:00Z`, and reopen at `11:00:00Z`. Requests remain available after case closure or withdrawal. These records do not submit an appeal, establish satisfaction or adjudicate a concern.

Use full RFC3339 UTC/offset timestamps. Case events, consent assertions and verification checks are nondecreasing across all three histories. Expected versions reject stale writes. Review requests have their own version and event chronology. Fictional IDs start `SYN-`; no individual or household identifier is needed.

## Proposed workflow rules

INTAKE → REFERRED → HANDOFF_ACCEPTED → SERVICE_STARTED → FOLLOW_UP. Referrals can be RETURNED and referred again; service can be SERVICE_INTERRUPTED and referred again. Before service, cases may close as CLOSED_NO_SERVICE; interrupted cases may also close without current service. CLOSED_WITH_SERVICE requires a passing check for the latest service-start event. Case closure is terminal in this prototype, while review requests can continue independently.

Referral, handoff acceptance, service-start and follow-up require a current RECORDED consent assertion. NOT_RECORDED and WITHDRAWN create a hold on those actions. Recording returns, interruptions, closure or review-request history does not require that assertion, because these records preserve uncertainty and concerns rather than initiate outreach. Actual consent standards, withdrawal handling and lawful retention must be confirmed separately; the prototype rule is not a legal conclusion.

A check must refer to the exact service-start/follow-up event, use a distinct verifier identifier from its recorder and include evidence. Identifiers and results are user assertions, not authenticated independent review. UNKNOWN continuity remains unknown even when the accuracy of that recorded observation is checked. An interruption invalidates any interpretation of an earlier continuing-follow-up as a current service condition.

## Measures

| Measure | Definition and limits |
| --- | --- |
| Referral-to-service hours | First referral to first service-start event with a passing event-specific check visible at cutoff. Repeated referrals do not reset the clock |
| Unverified referral age | First referral to cutoff for nonterminal cases without a verified start; includes recorded-but-unverified starts as unresolved evidence, not proven lack of service |
| Returned referrals | Number of recorded returns, not unique people or an independently established failure rate |
| Closed without service | Current CLOSED_NO_SERVICE stage, including closure after an earlier service interruption; does not erase a prior start or mean service never occurred |
| Consent holds | Current NOT_RECORDED or WITHDRAWN assertions, including closed cases; not a legal consent assessment |
| Continuity | Latest current-cycle follow-up, with event-specific passing check, distinguished as CONTINUING, UNKNOWN or unverified; no follow-up and interruptions remain separate |
| Interruptions | Recorded event count and cases whose latest service/interruption event is an interruption, even if the case later closes without current service or re-enters referral |
| Follow-up plans | Active SERVICE_STARTED/FOLLOW_UP cases with missing due plans or due times strictly before cutoff. No automatic contact or reminder is sent, including during a consent hold |
| Review requests | Open/reopened requests, original-request-to-latest-response time, and censored open-request age. RESPONDED does not mean adjudicated or resolved |

All measures use UTC calendar time. Historical cutoff selects visible records in each history before computing results; program and area filters use exact matches. Empty samples remain null with explicit counts; medians and nearest-rank P90 are descriptive synthetic statistics. Unknown identities, comparisons, service quality, causal effects and actual placement outcomes are not inferred. Denominators are fictional cases/events, not unique people, households or population coverage.

## Privacy and operating boundary

The structured model has no client names, addresses, housing histories, contact details, application/benefit identifiers or eligibility calculations. Use only fictional non-identifying scenario text; free text is not a redaction system. Do not upload protected notices or case files. The optional reference label does not verify a notice or its applicability. No real referral, placement, outreach, eligibility determination or legal review occurs.

## Interfaces and persistence

- `GET /api/housing` returns fictional cases and review requests.
- `POST /api/housing/cases` records intake.
- `POST /api/housing/cases/{id}/consents` records a consent assertion.
- `POST /api/housing/cases/{id}/events` appends a permitted lifecycle event.
- `POST /api/housing/cases/{id}/checks` checks the current start/follow-up event.
- `POST /api/housing/requests` opens a fictional review request.
- `POST /api/housing/requests/{id}/events` records a response or reopening.
- `GET /api/housing/report?as_of=...&program=...&area=...` computes historical measures.

The shared server uses loopback binding, host/origin protections and a local mutation token. Full JSON exports and SQLite backups include cases, events, consent assertions, checks, review requests and audit history. See [backup/restore](APPLICATION.md#export-backup-and-restore).

## Outstanding acceptance

Import and review the full source; confirm program boundaries, responsible institutions, actual consent and notice practices, review routes, retention/access requirements, accessible support and lawful aggregate measurement. Qualified acceptance and institutional authorization remain separate. This prototype does not mark project 013 complete or alter the original Layer A hold and pinned packet.
