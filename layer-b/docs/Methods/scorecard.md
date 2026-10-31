# Balanced operational scorecard

Use transparent definitions and counter-metrics, not a single ranking that hides critical
failures. Comparability needs equivalent service/case definitions, periods and populations.

| Dimension | Candidate indicators | Counter-metric or caveat |
| --- | --- | --- |
| Effectiveness | Intended service outcomes | External influences limit attribution |
| Efficiency | Cost/time per completed service | Monitor quality, exclusions and rework |
| Fiscal stewardship | Variance, reconciliation, audit closure | Underspend may indicate delayed services |
| Procurement | Competition, acceptance and performance | Interpret exceptions by law and market |
| Workforce | Capacity, retention and skill coverage | Headcount is not capability |
| Records | Completeness, retrieval and provenance | Access must preserve protected information |
| Infrastructure | Reliability, condition and maintenance | Deferred work hides lifecycle costs |
| Equity/accessibility | Outcomes across relevant populations | Averages can hide exclusion; protect small groups |
| Resilience | Continuity and recovery | Include safety and quality after restoration |
| Accountability | Verified correction and repeat-failure reduction | Closure counts alone do not verify a remedy |

## Indicator specification

For each indicator record metric_id, definition, unit, value, numerator, denominator,
reporting_period, source_id, exclusions, uncertainty, owner, revision and counter_metric.
The schema permits null value to represent no measurement, never zero by default.
Use a reasoned string for numerator/denominator when not a ratio, e.g. not applicable:
median of completed cases. Define units and avoid mixing time, effort and money.
source_id references a packet evidence entry; counter_metric is the paired safeguard's
definition or stable ID, not proof that the safeguard was measured.

The sample_size field reports available observations; zero means the synthetic pilot
has no observed performance data, and requires a null value. Do not claim an improvement from a null baseline.

## Project 048 interface

These definitions are intended to support later validation work associated with Project 048.
No Project 048 schema, service integration, endorsement or completed validation is claimed.
A Layer D evidence record should preserve provenance, transformations, uncertainty,
reproducibility, counter-hypotheses and source applicability.
