# Versioned synthetic cross-layer exchange

This local integration fixture demonstrates the interface proposed in
[cross-layer integration](../../cross-layer-integration.md). It is not a live integration
with other repositories or an adopted Layer B/C/D standard.

[exchange.json](exchange.json) contains versioned synthetic Layer B proposal, Layer C
outcome questions and Layer D evidence metadata, plus a pinned reference to the pilot's
Layer A review. The [exchange schema](../../schemas/cross-layer-exchange.schema.json)
is version 0.1.0, separate from the unchanged Layer A review schema 0.1.0.

## Contract

| Part | Identity and contents |
| --- | --- |
| Envelope | schema_version, exchange_id and explicit SYNTHETIC kind |
| Layer B | Version, stable proposal_id and summary |
| Layer C | Version, matching proposal_id, outcome questions and affected-population prompts |
| Layer A reference | Repository-relative path, SHA-256 of exact bytes, review_id, proposal_id, schema version and revision |
| Layer D | Version, record_id, matching proposal_id, evidence IDs, pinned source manifest and explicit uncertainties |

All paths are relative to the repository root, regardless of working directory.
The consumer rejects absolute paths, parent traversal and paths resolving outside that root.
Hashes bind exact file bytes, including newlines; they detect changed content but do not
authenticate an author, reviewer or external source.

## Consumer behavior

1. Validate the envelope and each proposed inline record against the supported version.
2. Require a common proposal_id across B, C, the A reference and D.
3. Read the pinned A record, verify its hash and validate it with the existing review schema.
   Require the reference's ID, proposal, schema version and revision to match the actual record.
4. Verify the manifest hash and pilot review ID; reject duplicate or unknown evidence IDs
   and evidence omitted from D that the A record references.
5. Report the actual Layer A status and keep the exchange blocked. This initial fixture
   requires nonempty D uncertainties, so it cannot represent a ready or approved exchange.

Duplicate JSON keys, NaN/Infinity constants and non-UTF-8 pinned JSON are rejected before
schema or reference checks. Malformed or mismatched exchanges exit 1. Valid structure exits 0 while reporting BLOCKED;
--require-ready exits 2. Downstream actions must not interpret structural success as permission.
No institution is authorized, no legal review is invented, and the consumer sends no requests.

The validator verifies manifest identity and evidence-ID membership. It does not fetch source
documents, validate source contents or dates, assess legal authority, or enforce cross-repository
permissions, signatures, historical revision ordering or freshness. The pilot tests separately
check the synthetic manifest's local source links.

## Reproduce

From the repository root after installing requirements-dev.txt:

```sh
python -m scripts.validate_exchange examples/cross-layer/exchange.json
python -m scripts.validate_exchange --require-ready examples/cross-layer/exchange.json
python -m unittest discover -s tests -v
```

Expected exchange exit codes are 0 and 2 respectively. Tests cover mismatched identities,
stale hashes and revisions, unknown evidence, unsupported versions and unsafe reference paths.

## Version and change handling

A producer changing the referenced record must retain its stable review/proposal IDs,
increment its review revision, preserve previous versions and regenerate the envelope's
reference metadata and exact-byte hash. A manifest change also requires an explicit hash
update and reassessment of evidence references. Never silently resolve a reference to latest.

These checks provide snapshot consistency, not proof that the snapshot is the newest version.
A production consumer must define an authoritative repository/ref, freshness policy, access
controls and authenticated provenance with the affected layer maintainers.
Incompatible contract changes require a new schema version, matching fixtures, negative tests
and review by affected maintainers. This 0.1.0 fixture accepts only its explicit version.

## Recorded outcome

The referenced pilot is revision 2, LEGAL_REVIEW_REQUIRED. Jurisdiction, governing authority,
required procedures and authorized reviewer assignment remain unresolved. Layer C's questions
do not justify bypassing that hold; Layer D's synthetic evidence does not certify legality.
The result remains BLOCKED.
