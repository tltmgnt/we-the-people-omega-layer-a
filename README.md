# WE THE PEOPLE Ω — Layer A

Layer A defines a foundational review architecture for constitutional, legal and democratic conditions across WE THE PEOPLE Ω systems. This alpha repository contains documentation, a synthetic review record, and structural validation tooling.

## Start here

- [Foundational architecture and seven proposed domains](Docs/Architecture/Layer-a-overview.md)
- [A1–A7 domain checklists](Docs/Domains/README.md)
- [Assurance gate, statuses and validation instructions](Docs/Assurance/review-gate.md)
- [Review JSON Schema v0.1.0](schemas/review-record.schema.json)
- [Hypothetical review record](example-review.json)
- [Reproducible benefits-process pilot](pilots/benefits-process/README.md)
- [Cross-layer integration](cross-layer-integration.md) and [versioned synthetic exchange](examples/cross-layer/README.md)
- [Contribution guidance](CONTRIBUTING.md) and [changelog](CHANGELOG.md)
- [Roadmap](ROADMAP.md) and [0.2.0-alpha release criteria](Docs/Releases/0.2.0-alpha.md)
- [License selection status](LICENSE-SELECTION.md)

## Current scope

The example intentionally remains LEGAL_REVIEW_REQUIRED. Structural validation does not determine legal sufficiency, verify reviewer authority or authorize implementation. Qualified human review and any separately required institutional decision remain necessary.

A synthetic intake-to-escalation pilot demonstrates a blocked outcome. A1–A7 checklists provide proposed review prompts and evidence requirements. The roadmap defines alpha acceptance criteria and subsequent work. A jurisdiction-specific pilot with qualified human review and operational integrations remain planned work.

## Quick check

With Python 3.12, from the repository root:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/validate_review.py example-review.json
```

The example passes structural validation and prints BLOCKED. See the assurance gate for the optional readiness check and exit codes.

## Foundational reference starting points

- U.S. Constitution (National Archives): https://www.archives.gov/founding-docs/constitution
- Bill of Rights (National Archives): https://www.archives.gov/founding-docs/bill-of-rights
- Constitution Annotated (Congress): https://constitution.congress.gov/
- U.S. Election Assistance Commission: https://www.eac.gov/
- Bureau of Indian Affairs: https://www.bia.gov/

These are starting points, not exhaustive controlling authority. Check current, applicable constitutional text, statutes, treaties, Tribal law, judicial decisions, and jurisdiction-specific requirements before relying on any legal conclusion.
