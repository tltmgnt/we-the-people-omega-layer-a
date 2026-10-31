# WE THE PEOPLE Ω — Layer B
## Government Operations

**Institutional Capacity · Public Finance · Procurement · Civil Service · Records · Public Works · Essential Services**

Layer B evaluates how federal, state, local and authorized intergovernmental institutions
convert lawful authority, public funding, personnel, information and infrastructure into
reliable, accessible and accountable public services.

**Central question:** Can institutions translate public mandates and authorized resources
into measurable public value while preserving accountability, continuity and constitutional constraints?

Layer A establishes the constitutional/legal boundaries. Layer B organizes operational
analysis within them. These six analytical domains do not replace departments, legal
responsibilities or distinct Tribal authority.

| Domain | Scope |
| --- | --- |
| [B1 Institutional operations](docs/domains/B1-institutional-operations.md) | Understand how public institutions translate mandates into coordinated operations while maintaining clear authority and accountability. |
| [B2 Budgets and public finance](docs/domains/B2-budgets-and-finance.md) | Trace public resources from authorization to actual use and verified public outcomes. |
| [B3 Procurement and contracts](docs/domains/B3-procurement-and-contracts.md) | Examine whether purchases are authorized, appropriately competed, managed and verified against delivered goods, services or works. |
| [B4 Civil service and public workforce](docs/domains/B4-civil-service.md) | Assess whether institutions have the staffing, skills, leadership and working conditions needed to deliver services consistently. |
| [B5 Records and information](docs/domains/B5-records-and-information.md) | Maintain accurate records of institutional actions that support accountable operations and appropriate access, security and preservation. |
| [B6 Public works and essential services](docs/domains/B6-public-works-and-essential-services.md) | Evaluate whether infrastructure and essential services are safe, reliable, accessible, resilient and maintained at sustainable lifecycle cost. |

## Initiative goal

Layer B supports the broader proposed five-layer, 50-project civic research and institutional-improvement initiative. The immediate objective is framework review and one bounded, measurable government collaboration, not a claim of a validated government standard.

- [Five-layer alignment](docs/Architecture/five-layer-alignment.md)
- [50-project register and B crosswalk](portfolio/README.md)
- [Government collaboration and pilot brief](docs/Collaboration/concept-and-pilot.md)

## Start here

- [Run the 50-project portfolio application](portfolio/APPLICATION.md)
- [All 50 proposed implementation plans](portfolio/plans/README.md)

- [Architecture, mission and lifecycle](docs/Architecture/layer-b-overview.md)
- [TGA Ω gap matrix](docs/Methods/topological-gap-analysis.md)
- [Balanced scorecard](docs/Methods/scorecard.md) and [DTI Ω time/burden](docs/Methods/temporal-burden.md)
- [HedgeOps Ω analytical roles and controls](docs/Governance/hedgeops.md)
- [Governance and operational assurance](docs/Governance/assurance.md)
- [Layer A integration](cross-layer-integration.md)
- [Hypothetical permit pilot](examples/permit/README.md)
- [90-day roadmap](ROADMAP.md), [official research sources](docs/Research/sources.md)
- [Record contract](schemas/operational-review.schema.json), [changelog](CHANGELOG.md)
- [Contribution guidance](CONTRIBUTING.md), [security](SECURITY.md), [license decision](LICENSE-SELECTION.md)

## Current package

The local portfolio application supports source imports, editable delivery plans, evidence-backed progress, exports and backup. Project-specific domain services and the full linked source documents remain outstanding; see [delivered scope and remaining work](portfolio/APPLICATION.md).

A publicly imported **0.1.0-alpha preparation** in the [Layer A repository](https://github.com/tltmgnt/we-the-people-omega-layer-a/tree/main/layer-b). See [setup and acceptance](SETUP.md) for the current layout and remaining release work.
It includes proposed methods, a draft record schema, validation tooling and a synthetic
permit packet. No real institution, data connection, personnel evaluation, procurement
decision, legal approval or public-service change is represented as completed.

The TGA Ω, DTI Ω and HedgeOps Ω names are project methods proposed in the supplied
framework; this package does not claim external validation or institutional adoption.

## Validate locally

Use Python 3.12 from the `layer-b/` directory (run `cd layer-b` from the repository root):

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m scripts.validate_packet examples/permit/operational-review.json
python -m scripts.validate_packet --require-ready examples/permit/operational-review.json
```

Expected: tests exit 0; packet validation exits 0 and prints BLOCKED; --require-ready
exits 2. Structural validity never authorizes execution. See the [assurance contract](docs/Governance/assurance.md).

## Defining principle

Government operations are the bridge between public authority and public outcomes.
Evaluate whether that bridge works, preserves trustworthy records, maintains enduring
assets, supports a capable workforce and corrects failures before they become permanent.
