# Hypothetical permit-processing pilot

All institutions, owners and service details here are fictional. No actual California
agency, employee, applicant, permit rule or performance result has been evaluated.

## Bounded proposal

A fictional local permitting office wants to diagnose a growing application backlog
before proposing any change. The initial observation is a scenario assumption, not measured
evidence. The legal jurisdiction, permit type, governing authority and service obligations
are not identified. No staffing, spending, automation or safety-inspection change is authorized.

The purpose is a validated explanation and testable improvement plan, not a presumption
that staff, applicants or the institution are at fault.

## Lifecycle and ownership map

| Stage | Candidate function | Evidence to request |
| --- | --- | --- |
| Mandate | Identify program, authority and responsible institution | Applicable sources and owner |
| Planning | Estimate demand, staffing and service obligations | Demand/case-mix baseline |
| Readiness | Check skills, tools, accessible channels and procedures | Capacity and access assessment |
| Delivery | Intake, review, handoff, inspection and decision | Timestamped stage/queue records |
| Verification | Check accuracy, safeguards and record completeness | Independently assessed sample |
| Correction | Address errors and verified causes | Remedy owner, bounded trial and rollback |
| Learning | Monitor sustained results and training | Follow-up after temporary support ends |

Operational, assurance and public-accountability owners remain unassigned. Map actual
decision rights and necessary legal/safety stages before redesigning the process.

## Competing hypotheses

| Hypothesis | Distinguishing evidence | Safeguard |
| --- | --- | --- |
| Incomplete inputs create repeated cycles | Completeness at intake, requests for correction, case mix | Do not blame applicants or remove assistance |
| Specialist capacity is constrained | Qualified workload, vacancies, service mix and tools | Do not infer individual underperformance |
| Sequential departmental review creates queues | Handoff/event timestamps and actual dependencies | Preserve required review and inspection |
| Status uncertainty causes avoidable contact/rework | Authorized journey research and repeat inquiries | Preserve accessible nondigital routes |
| Demand exceeds planning assumptions | Comparable arrivals, completions and seasonal patterns | Do not treat demand as misconduct |
| Necessary legal or safety work explains duration | Applicable requirements and verified task content | Do not delete required safeguards for speed |

Several explanations may operate together. Before assigning causes, assess missing data,
case complexity, selection effects and alternative interpretations. Use a controlled
simulation until actual data access and institutional approval are established.

## Metric design

The packet defines elapsed time, public effort and decision accuracy with null values
and zero observations. There is no measured baseline or result. Pair shorter elapsed
time with accuracy, appeal outcomes, access, safety, abandonment and rework.

Specify start/end events, paused cases, time zone/calendar, business versus elapsed time,
open/censored cases and equivalent permit categories. Measure staff effort, queue time,
handoffs, coordination, recovery and transferred public burden separately; do not add
overlapping components into an unvalidated composite index.

## Recorded preparation gap

GAP-PERMIT-001 concerns the missing end-to-end measurement and authority baseline in this
synthetic design. MODERATE is qualitative preparation triage, not an allegation about a
real office or an estimated public harm. The proposed remedy is to define boundaries,
lawful access and competing-hypothesis tests before a bounded study.
The gap remains OPEN and its operational/assurance owners are unassigned.

## Layer A hold and evidence boundary

[layer-a-review.json](layer-a-review.json) is a newly written synthetic record following
the upstream A schema; it is not an upstream legal decision. It has no actual reviewer
identity or review timestamp and remains LEGAL_REVIEW_REQUIRED.

[operational-review.json](operational-review.json) references that record and this note
with exact-byte SHA-256 hashes. The note is the synthetic scenario/triage source, not
empirical evidence or authority. The evidence ID is SYNTHETIC-PERMIT-NOTES-001.

## Reproduce

From repository root after installing requirements-dev.txt:

```sh
python -m unittest discover -s tests -v
python -m scripts.validate_packet examples/permit/operational-review.json
python -m scripts.validate_packet --require-ready examples/permit/operational-review.json
```

Expected exits: 0, 0 with BLOCKED, and 2 with BLOCKED. Updating the source note or A fixture
requires explicit hash regeneration and reassessment. A changed file must not silently pass
as the earlier evidence. No external reads, messages or service changes occur.

## Completion boundary

This is an intake/diagnostic design exercise. A real pilot requires selected jurisdiction
and program, an accountable participating institution, qualified Layer A review, authorized
data access, measured baseline, independent verification and separate human decisions.
