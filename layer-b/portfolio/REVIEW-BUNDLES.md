# Selected synthetic review bundles

Download selected scenario snapshots/comparisons as a ZIP with exact source references, current-at-export flags, workflow definitions, the user-supplied A–E summary, checksums and a standalone verifier.

This is a portable review artifact, not a full database backup, source-code distribution, authenticated legal record or institutional acceptance. It does not fetch the linked Google Docs or certify the proposed architecture.

## Interface

Start from layer-b:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/review-bundles>, or choose **Download selected review bundle** in the controller.

1. Enter a unique-looking SYN- bundle label, actor identifier and purpose/sharing limitations.
2. Select one or more current snapshots. Enable historical snapshots if needed.
3. Select saved comparisons if desired; their baseline/alternative snapshots are resolved automatically.
4. Download the ZIP. Capstone source snapshots are recursively included so their references can be checked.
5. Review index.json, README.txt and the selected actor notes/measurements before sharing. Nothing is sent to another person or published automatically.

Only selected snapshots/comparisons, their scenario dependencies and definitions are included. Imported source documents, unrelated runs, the entire audit log and unrelated domain-lab records are excluded. Selected snapshots may still contain text entered by an operator, so a checksum does not make them suitable for public disclosure.

## Archive contents

| File/group | Content |
| --- | --- |
| manifest.json | Format/version, bundle label, build time and every other file's SHA-256/byte count; explicitly unsigned |
| index.json | Requested versus resolved scope, source paths, actor and purpose |
| snapshots/ | Exact source event/state, sequence, workflow, state hash and locally asserted current-at-export status |
| comparisons/ | Selected frozen comparisons, definitions, arithmetic and current export-time diagnostic flags |
| definitions/ | Current definitions for included workflows; saved comparisons keep their own frozen metric definitions |
| architecture/five-layer-summary.json | User-provided A–E descriptions/source links; full linked documents not imported |
| boundary.json | SYNTHETIC, execution unauthorized, Layer A LEGAL_REVIEW_REQUIRED, institutional acceptance NOT_ESTABLISHED |
| README.txt | Verification and interpretation limits |
| verify_bundle.py | Standalone convenience copy of the trusted repository verifier |

Current/historical flags are local database assertions at build time, not live guarantees. Snapshot pins and comparison results remain historical. Missing/mismatched referenced snapshots or corrupted comparison sources reject the build rather than silently omit evidence.

## Verify independently

Prefer the trusted repository copy:

    python -m scripts.verify_review_bundle selected-review.zip

The verifier uses only Python's standard library, extracts no files and contacts no network. Exit 0 means file checksums/lengths, bounded safe archive names, snapshot hashes, dependency/comparison references, saved arithmetic and fixed boundary fields passed its structural checks. Invalid archives exit 2.

The included copy can be run after manual inspection, but an untrusted ZIP cannot authenticate its own verifier or manifest. Hashes are **not signatures** and do not prove authorship, source truth, complete chain of custody, lawful authority, causal effects, method validity or real outcome effectiveness.

Limits are 100 explicitly selected snapshots, 20 comparisons, 200 resolved snapshots, 512 archive entries, 8 MiB per file and 32 MiB total. The verifier rejects duplicate/unlisted names, traversal/absolute paths, symlinks, excessive expansion, modified files, changed snapshot hashes, inconsistent references/arithmetic and altered authority boundaries.

## CLI export

    python -m civic_portfolio export-review-bundle \
      --bundle-id SYN-REVIEW \
      --snapshot SYN-DEMO-V1-024:10 \
      --comparison SYN-COMPARISON \
      --actor "REVIEWER" \
      --note "Selected fictional scope; review before sharing" \
      --output selected-review.zip

Use actual existing sequence numbers, inspect them in the controller first. Either --snapshot or --comparison must select something. Repeat either flag for additional selections. Existing output files are never overwritten. Use --db before the command to select a workspace.

POST /api/review-bundles accepts bundle_id, selections=[{run_id,sequence}], comparison_ids, actor and note; it uses the existing loopback Host/origin/token controls. Response is application/zip with a validated attachment filename. A successful build appends an audit record with scope and archive hash. That record proves a build occurred, not delivery, sharing or reviewer acceptance. Source scenario/comparison/project records remain unchanged.

## Architecture location

The repository's [central five-layer index](../../Docs/Architecture/README.md) links individual A–E summaries and existing detailed A/B documents. C/D/E now have dedicated synthetic workspaces, documented in [LAYER-WORKSPACES.md](LAYER-WORKSPACES.md). Their evidence/outcome/rehearsal records are outside this selected scenario ZIP; these remain prototypes rather than complete institutional implementations. The bundled machine-readable summary preserves this distinction and the supplied source URLs.

## Verification and handoff

    python -m unittest tests.test_review_bundles -v

Tests cover selected-scope exclusion, A–E metadata, both comparison sources, transitive capstone dependencies, checksum/state/reference/arithmetic integrity, forged boundary rejection, unsafe/extra/duplicate names, invalid/oversized selections, source immutability/build audit, guarded HTTP and trusted CLI verification/no-overwrite. Browser CI downloads a selected snapshot+comparison archive and verifies it using the trusted repository script, then checks mobile layout.

For full workspace recovery use the separate SQLite backup command; this selected artifact does not restore a workspace. Keep backups and exports appropriately private. Real source import, qualified review, 001–006 definitions and institutional acceptance remain outstanding.
