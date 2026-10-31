# Cross-layer integration

- **Layer A:** Owns constitutional legitimacy review requirements, jurisdiction and rights-assurance criteria.
- **Layer B:** Supplies institutional processes and proposed operational actions subject to Layer A constraints.
- **Layer C:** Supplies outcome questions and affected-population considerations subject to applicable rights and authority.
- **Layer D:** Supplies evidence provenance, uncertainty, reproducibility, and validation methods; it cannot independently certify legality.

## Interfaces
A proposal references a versioned Constitutional Legitimacy Record and, where available, a Layer D Evidence-to-Decision Record. Cross-repository contracts should use stable identifiers, explicit schema versions, and change review by affected maintainers.

## Portfolio examples
Projects 016–017 (rights/elections), 019/033 (integrity), 040 (intergovernmental and Tribal governance), 042–045 (evidence/intelligence), 046–049 (transition/assurance), and 050 (simulation) should reference Layer A constraints rather than duplicate them.

## Versioned local exchange example

The [synthetic exchange](examples/cross-layer/README.md) demonstrates a common proposal ID
across proposed B/C/D records, an exact-byte hash and revision reference to the Layer A
pilot, and pinned evidence-manifest references. Its consumer rejects inconsistent or
unsupported records and reports the blocked outcome. It is a local proposed contract,
not an adopted external layer schema or live cross-repository connection.
