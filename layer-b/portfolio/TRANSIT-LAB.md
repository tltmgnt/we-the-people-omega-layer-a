# Project 012 — synthetic transit reliability and access

## Delivered scope

The local application provides fictional scheduled trips, versioned arrival/cancellation observations, verification tied to the current observation, configurable on-time windows, measured aggregate passenger-delay records and separate accessibility findings with response/reopening histories. Each trip represents **one declared arrival boundary**, not a full route or a series of stops. The prototype follows the [editorial project plan](plans/012.md), not the unread linked source document.

From `layer-b/`, run `python -m civic_portfolio serve` and open <http://127.0.0.1:8765/transit>. Restart an existing server to add the routes and tables. Existing portfolio and domain-lab records remain intact; no fictional trips or measurements are inserted automatically.

## Fictional walkthrough

1. Enter an operator identifier. Schedule `SYN-TRIP-001`, service `Demo line · terminal arrival`, area `Demo area`, registered at `2026-01-01T00:00:00Z`, with scheduled arrival `2026-01-01T10:00:00Z` and fictional schedule evidence.
2. Record ARRIVED at observation time `2026-01-01T11:00:00Z`, actual arrival `2026-01-01T10:05:00Z`, and explicit evidence. Optionally record 2 aggregate passenger observations and 20 aggregate person-minutes of delay. These are separate supplied measurements, not inferred from the five-minute vehicle deviation.
3. Verify that observation at `2026-01-01T12:00:00Z` using a distinct verifier identifier and evidence. At cutoff `2026-01-02T00:00:00Z`, the prototype's inclusive early/late window of 1/5 minutes classifies this arrival as on time. The measured passenger mean is 20 / 2 = 10 minutes per passenger observation.
4. Record `SYN-ACCESS-001` for that trip, category MOBILITY, timestamp `2026-01-01T10:10:00Z`, with a fictional non-identifying access barrier and 2 reported excluded boarding observations. An on-time vehicle does not resolve the access finding.
5. Correct the trip observation at `2026-01-01T12:00:00Z` to actual arrival `10:06:00Z`. Prior observations remain in history. The old check becomes stale, even at the same timestamp. Leave passenger fields blank if the revised observation has no confirmed passenger measurement; the application does not carry forward an unconfirmed value.
6. Verify the revised observation at `13:00:00Z`. This trip is now late under the default five-minute tolerance. A corrected earlier arrival can also be recorded because actual arrival time is separate from the later revision timestamp.
7. Schedule `SYN-CANCEL-001` for arrival `14:00:00Z`, registered at midnight. Record CANCELLED at `13:00:00Z` with no actual-arrival timestamp and verify at `14:00:00Z`. After both trips are due, the on-time arrival rate is 0/1, while cancellation rate is 1/2 verified outcomes. No zero-delay observation is invented for the cancellation.
8. Resolve the access finding at `14:00:00Z` with response evidence, then reopen at `15:00:00Z` with a new observation. This changes the accessibility history independently of trip outcome records.

All timestamps require RFC3339 UTC or numeric offsets and normalize to UTC. Schedule registration cannot follow scheduled arrival. Actual arrival must be at or before its observation/revision timestamp and not before registration. Revision and verification timestamps are nondecreasing. New revisions invalidate previous checks by exact observation sequence. Expected versions reject stale writes. A distinct verifier identifier is required; identifiers and results remain user assertions, not authenticated independent findings.

## Measurement contract

| Measure | Definition and boundary |
| --- | --- |
| Due scheduled trips | Registered trips scheduled at or before cutoff |
| Upcoming trips | Registered trips scheduled after cutoff, including early-recorded cancellations; kept outside due-trip outcome statistics |
| Unobserved/unverified | Due trips without a visible observation or without a passing current-observation check; explicitly excluded from verified outcome rates |
| Verification coverage | Verified outcomes / all due scheduled trips; exposes missing evidence alongside reliability rates |
| On-time arrival rate | Verified arrivals within inclusive `[-early, +late]` minute window / all verified arrivals. Defaults 1/5 minutes are a proposed prototype choice, not an official standard |
| Cancellation rate | Verified cancellations / verified arrivals plus cancellations; cancellations are not zero-delay arrivals |
| Arrival deviation | Signed actual minus scheduled arrival minutes; early arrivals remain negative |
| Positive arrival delay | Maximum of zero and arrival deviation for verified arrivals; a vehicle-time measure, not passenger burden |
| Passenger delay | Supplied aggregate person-minutes / supplied passenger observations across verified outcomes with both fields. Zero counts require zero total delay; zero denominator gives a null mean |
| Missing passenger data | Verified outcomes without the required pair; not inferred from vehicle delay or assumed zero |
| Access findings by need | Separate finding/open/resolved counts and optional excluded-boarding observations by category; unknown exclusion totals remain null |
| Access response/open age | Original finding to latest resolution, or original finding to cutoff for open/reopened findings; medians and nearest-rank P90 with explicit sample sizes |

Historical cutoff selects visible observation/check revisions first. Service and area filters are exact matches. A trip that is early by more than the selected early tolerance is outside the on-time window. Passenger observations across trips are not necessarily unique people. Access findings may overlap; exclusion observations are not a unique rider count, disability prevalence, boarding-denial rate or population coverage. Findings for registered upcoming trips can appear before the trip is due, allowing fictional advance-access observations. No confidence interval, causal attribution or real-world service finding is provided.

## Privacy and operating boundary

The structured model contains no passenger name, address, contact information or individual disability record. Use only invented identifiers and non-identifying aggregate/scenario text. Free text is not an anonymization or redaction system. No actual dispatch, passenger communication, trip scheduling in an agency system or accessibility certification occurs. An arrival record never automatically resolves an access finding.

## Interfaces and persistence

- `GET /api/transit` returns trips and access findings.
- `POST /api/transit/trips` registers a fictional scheduled arrival boundary.
- `POST /api/transit/trips/{id}/observations` appends an arrival/cancellation observation or correction.
- `POST /api/transit/trips/{id}/checks` verifies the current observation.
- `POST /api/transit/findings` records a fictional access finding.
- `POST /api/transit/findings/{id}/events` resolves or reopens a finding with evidence.
- `GET /api/transit/report?as_of=...&service=...&area=...&early_minutes=1&late_minutes=5` computes descriptive reports.

Routes use the shared local mutation token, host/origin protections and loopback-only server. Full JSON export and SQLite backup contain trip, observation, check, access and audit histories. See [backup/restore](APPLICATION.md#export-backup-and-restore).

## Outstanding acceptance

Import and review the full project source; select an actual service and arrival boundary; confirm schedule changes, time windows, cancellation definitions, accessible reporting, lawful aggregate data collection and verification responsibilities. Qualified acceptance and institutional authorization remain separate. The prototype does not mark project 012 complete or change the original Layer A hold and pinned synthetic packet.
