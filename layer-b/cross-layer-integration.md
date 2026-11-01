# Layer B cross-layer integration

| Layer | Responsibility | Boundary |
| --- | --- | --- |
| A | Constitutional/legal review, jurisdiction and rights safeguards | B cannot override a hold or manufacture authority |
| B | Institutions, resources, processes, assets, delivery and correction | Operational findings are not legal or misconduct findings |
| C | Outcome questions and affected-population considerations | Outcomes cannot justify bypassing rights or authority |
| D | Provenance, uncertainty, reproducibility and validation | Evidence quality cannot independently certify legality |
| E | Controlled pilots, transition, corrective action, adoption and institutional learning | Diagnostic findings do not authorize implementation; independent evaluation and human decisions remain necessary |

The packet uses stable proposal_id, record_id, review_id and evidence_id values and explicit
schema versions. A local reference pins Layer A review revision, schema version and SHA-256
of exact bytes. It is a synthetic reference, not a claim that the new permit review exists
in the Layers A–E repository. See [upstream provenance](vendor/layer-a/UPSTREAM.md).

The Layer A [synthetic exchange example](https://github.com/tltmgnt/we-the-people-omega-layer-a/tree/main/examples/cross-layer)
has its own proposed 0.1.0 envelope. This Layer B operational record is a separate draft
contract and does not claim automatic compatibility or adopted external B/C/D standards.
A future adapter needs a reviewed field mapping and shared proposal identity.

## Compatibility rules

Do not silently select latest. Retain source provenance, exact schema version, revision
and hash; verify IDs against actual content. A changed proposal needs reassessment.
Do not reinterpret statuses or convert structural success into authorization.
Hashes bind bytes, not authentic authorship, current validity or reviewer qualifications.
Production references need agreed repository/ref, authenticated provenance, permissions,
freshness and revocation handling. No live connection is supplied here.

See the [full five-layer alignment](docs/Architecture/five-layer-alignment.md) and [collaboration brief](docs/Collaboration/concept-and-pilot.md) for the broader initiative goal.
