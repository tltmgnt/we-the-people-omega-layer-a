# Portfolio application and implementation plans

## Delivered scope

The local application provides a working delivery workspace for all 50 registered proposals: search/filter, project definitions, accountable owners, proposed plans, completion evidence, source-text import/review, content hashes, immutable source versions, a change history, JSON export and SQLite backup.

A project-specific [synthetic permit lab for project 009](PERMIT-LAB.md) is also available at `/permits`. It demonstrates case progression, correction loops, time/effort measurement and quality reviews using fictional records. It is not a live permit system or a completed project acceptance.

The [synthetic maintenance lab for project 010](MAINTENANCE-LAB.md), at `/maintenance`, adds assets, condition reports, triage, work-order history, verification-before-closure, reopening and backlog/repair-time reports. It does not dispatch repairs or certify safety; the original source and actual process requirements still need review.

The [50 individual plans](plans/README.md) define proposed outcomes, input records, measurement and counter-metrics, safeguards, eight delivery steps and acceptance criteria. Plans 001–006 retain unresolved titles and source mapping. Plans 007–050 use the supplied titles and explicitly labeled editorial proposals. None is represented as a transcription of the linked document or a completed domain service.

## Run locally

Use Python 3.12 from `layer-b/`. The application itself uses only the Python standard library.

```sh
python -m civic_portfolio init
python -m civic_portfolio serve
```

Open <http://127.0.0.1:8765>. Data is stored in `.local/portfolio.sqlite3`; no cloud hosting or live government connection is configured. The service binds to loopback only. It is a local single-workspace tool, not an authenticated multi-user internet service.

Enter your name or identifier before making changes. That identifier is a local assertion, not a verified identity. Search or filter projects, select one and inspect its proposed plan. Save a project definition, then separately confirm its scope. Changing title or scope invalidates the previous work evidence and scope confirmation.

## Import the full documents

The source catalog includes 50 project slots, four unassigned foundational documents, five layer documents and two additional sources. Fifty-four slots have supplied URLs. Seven project slots (001–007) have no assigned URL. Source URLs are preserved as references; source content is not fetched automatically.

The Google Docs retrieval attempts for the permit source and first foundational source were unsuccessful in the preparation environment. No Google Drive connection was selected. Therefore **the linked documents' full contents are not included**. The application supports importing complete UTF-8 text, Markdown or JSON exports supplied by the owner. It does not convert PDF, Word or native Google Docs files.

In a source panel, choose the full text export or paste its content, record its original document URL or export identity, and import. Read the imported version before recording a review. Every import gets a timestamp, SHA-256 and revision; previous versions remain in the workspace. Importing a new project source clears that project's scope confirmation and completion evidence. Importing shared foundation/layer sources does not automatically invalidate dependent projects because those dependencies have not been confirmed; assess that impact explicitly.

The same operation is available from the command line:

```sh
python -m civic_portfolio import-source project-009 --file permit-source.txt --origin "original document URL or supplied export identity" --actor "your identifier"
python -m civic_portfolio review-source project-009 --revision 1 --actor "reviewer identifier"
```

Use `foundation-1` through `foundation-4`, `layer-a` through `layer-e`, `additional-formula` and `additional-curriculum` for shared documents. Do not assign the four foundational sources to projects 001–004 without confirming the mapping. A content hash detects content identity; it does not prove authorship, completeness or authenticity.

## Record delivery and acceptance

Each plan requires source review, confirmed scope, a data contract, baseline/counter-metrics, executable domain work, tests, reviewer acceptance and a reproducible handoff. Add a specific evidence reference and verification result for each completed step. Evidence is retained as an attributable text assertion; the application does not independently verify referenced results.

A project reports `COMPLETE_AS_RECORDED` only when it has a title, accountable owner, confirmed scope, an imported and reviewed current source, and completion evidence for all eight steps. Unknown source data and unperformed work remain open. The application never grants execution authorization, and the original packet validator continues to enforce the Layer A hold.

**Outstanding project-specific work:** import and review the real source documents; confirm 001–006; replace or accept the proposed requirements; implement and test each confirmed domain workflow beyond the bounded project 009 and 010 simulations; obtain qualified acceptance and resolve licensing. This shared delivery application and synthetic labs are not substitutes for those 50 accepted domain implementations.

## Export, backup and restore

```sh
python -m civic_portfolio report
python -m civic_portfolio export --output portfolio-export.json
python -m civic_portfolio backup --output portfolio-backup.sqlite3
python -m civic_portfolio --db portfolio-backup.sqlite3 report
```

JSON export contains all project records, source text versions and audit events. The SQLite backup is a restorable workspace: stop the server and run it with `--db portfolio-backup.sqlite3 serve`, or copy that backup to the desired database location while the server is stopped. Backup refuses to overwrite an existing file. Exported source contents and reviewer identifiers may be private; keep workspace data out of public git commits. Back up before moving or deleting local work.

## Verification

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m scripts.validate_packet examples/permit/operational-review.json
python -m scripts.validate_packet --require-ready examples/permit/operational-review.json
```

The readiness command must exit 2 for the supplied synthetic packet. Application tests cover all 50 IDs, generated-plan consistency, source hashes/version history, persistence, stale edits/reviews, invalid inputs, evidence requirements, source/scope invalidation, backup restoration, HTTP writes/exports and local-origin protections. Run `python -m scripts.build_implementation_plans` to regenerate plans from the proposed profiles; runtime edits remain in SQLite and do not rewrite the source register or generated plans.
