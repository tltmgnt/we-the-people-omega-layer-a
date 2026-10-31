# One-action fictional examples for all defined workstreams

The loader creates one inspectable synthetic example for every defined workstream, Projects 007–050. Existing runs, source text, project records and legal holds are preserved. Projects 001–006 remain definition-blocked.

## Load in the interface

Start the app from layer-b:

    python -m civic_portfolio serve --port 8765

Open <http://127.0.0.1:8765/scenarios>. Enter an identifier, choose a unique demo batch ID (default SYN-DEMO-V1), then click **Load 44 fictional examples**.

The selected run becomes the first example. Use **Choose scenario** to inspect all 44. Each example follows valid transitions to its declared completion and uses explicit fictional SYN-DEMO-RECORDER / SYN-DEMO-CHECKER identities. The 38 catalog profiles contain sample observations/counter-measures; the six specialized profiles retain their own existing diagnostic fields. Project 050 links the completed, observed Project 024 example.

All seed notes explicitly identify fictional demonstration records. A completed example is not an accepted project, lawful government action, measured institutional performance or actual method execution.

## CLI

    python -m civic_portfolio demo-scenarios --batch-id SYN-DEMO-V1 --actor "DEMO INITIATOR"
    python -m civic_portfolio serve --port 8765

Use --db before the command to select a workspace. The CLI prints the same receipt as the interface.

## Atomic and non-overwriting contract

- The entire batch runs in one SQLite transaction using the normal create/command validation, review separation, metric contracts and capstone evidence checks. Failure rolls back all new runs, events, audit records and the batch receipt.
- Run IDs are batch ID + project number, such as SYN-DEMO-V1-024. Batch IDs must be valid SYN- identifiers of at most 55 characters. If a proposed ID already exists without the matching batch receipt, loading rejects the batch before any new run is written.
- A saved receipt makes repeat loading idempotent. Existing examples are never reset, repaired or overwritten by reloading the same batch. Changes in run version or state hash are listed in changed_since_seed; missing runs are listed and prevent treating a repeat load as complete.
- Use a different batch ID for another example set. Earlier examples remain.
- Catalog changes are flagged in catalog_changed; the loader does not silently migrate an older batch or its snapshots.
- The receipt records fixture version, initiating identifier, creation timestamp, catalog hash, all run IDs/workflows/project IDs, seed versions and state hashes, plus six definition holds. These are local assertions, not authenticated signatures.
- Simulation actors/notes are fixed fictional fixture values. The actual loader initiator is recorded separately in the batch receipt and audit trail.
- Loading only writes scenario tables, demo receipts and associated audit events. It imports/reviews no source, marks no project complete and modifies no dedicated permit/justice/other domain-lab records.

Manual state/time/measurement edits work normally after loading. For example, advancing Project 024's clock makes the Project 050 reference stale; repeating the loader preserves both the source edit and the stale capstone. Reattach/review using the existing controls if you want another current fictional capstone.

## Inspect and recover

GET /api/scenarios includes demo_batches and all runs. POST /api/scenarios/demo accepts batch_id and actor and requires the shared mutation token. GET /api/scenarios/demo/{batch-id} returns a current receipt with changed/missing/catalog flags. created=true is returned only by a newly created batch; an idempotent load returns created=false.

    python -m civic_portfolio export --output demo-workspace.json
    python -m civic_portfolio backup --output demo-workspace.sqlite3
    python -m civic_portfolio --db demo-workspace.sqlite3 serve --port 8766

Workspace export includes synthetic_scenarios.demo_batches and full scenario history. Backups preserve receipts and changes. Keep exports private if other workspace data contains private source text. For rollback, stop the app and restore a copy of an untouched backup with the corresponding application version; do not overwrite the only backup.

## Verification and limitations

    python -m unittest tests.test_demo_scenarios -v

Tests cover all 44 completed fixtures, checks/observations/current capstone, repeat-load preservation, independent namespaces, collisions, injected mid-batch rollback including audit, source/project/domain isolation, missing/catalog flags, backup/receipt persistence, invalid metadata, guarded HTTP and CLI creation. Browser CI covers one-action loading, source edits, non-overwriting repeated load, stale capstone preservation, reload and mobile layout alongside previous workflows.

No automatic service, agent execution, adoption, public reporting or live intervention occurs. execution_authorized=false and Layer A LEGAL_REVIEW_REQUIRED remain fixed. Real source requirements and qualified institutional acceptance remain outstanding. [All 50 slots and coverage](CONTROL-COVERAGE.md).
