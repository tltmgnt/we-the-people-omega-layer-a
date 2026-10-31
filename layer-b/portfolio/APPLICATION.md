# Portfolio application and implementation plans

## Delivered scope

The local application provides a working delivery workspace for all 50 registered proposals: search/filter, project definitions, accountable owners, proposed plans, completion evidence, source-text import/review, content hashes, immutable source versions, a change history, JSON export and SQLite backup.

A project-specific [synthetic permit lab for project 009](PERMIT-LAB.md) is also available at `/permits`. It demonstrates case progression, correction loops, time/effort measurement and quality reviews using fictional records. It is not a live permit system or a completed project acceptance.

The [synthetic maintenance lab for project 010](MAINTENANCE-LAB.md), at `/maintenance`, adds assets, condition reports, triage, work-order history, verification-before-closure, reopening and backlog/repair-time reports. It does not dispatch repairs or certify safety; the original source and actual process requirements still need review.

The [synthetic sanitation lab for project 011](SANITATION-LAB.md), at `/sanitation`, records route runs, verified cumulative service totals, recovery revisions and anonymous report responses. It separates stop-visit denominators, verification gaps, recovery times and repeat reports. No household-level fields, actual collections or dispatch are provided.

The [synthetic transit lab for project 012](TRANSIT-LAB.md), at `/transit`, records scheduled arrival boundaries, verified arrivals/cancellations, explicit aggregate passenger delay and independent accessibility-finding histories. It exposes verification coverage and missing passenger measurements alongside on-time reports; no actual dispatch or passenger-level records are provided.

The [synthetic housing referral lab for project 013](HOUSING-LAB.md), at `/housing`, records consent assertions, referral/handoff stages, verified starts and follow-up, interruptions and review-request responses. No client-level identity fields, actual referrals, benefit decisions or outreach are provided.

The [synthetic records and meetings lab for project 014](PUBLIC-ACCESS-LAB.md), at `/public-access`, tracks request/complaint scope, captured external due assertions, handoffs/reopening and checked meeting-notice/access references. It calculates no legal deadlines and sends or publishes no requests, responses or notices.

The [synthetic utilities-continuity lab for project 015](UTILITIES-LAB.md), at `/utilities`, records assets, interruption/restoration cycles, scenario-quality checks and aggregate incident-associated connection-hours. It exposes unknown counts and escalation-route gaps without operating utilities, dispatching repairs or certifying safety.

The [synthetic rights-evidence lab for project 016](RIGHTS-LAB.md), at `/rights`, records A1–A7 screening, exact-text snapshots, pinned questions/challenges and unassessed authority candidates. Its schema-compatible Layer A draft export always remains LEGAL_REVIEW_REQUIRED; local coverage never creates qualified review or execution permission.

The [synthetic election-service lab for project 017](ELECTION-SERVICES-LAB.md), at `/election-services`, records scenario readiness, anonymous administrative-access observations and checked correction/reopening histories. It processes no voter-level records, ballots or results and makes no election-validity or representation judgment.

The [50 individual plans](plans/README.md) define proposed outcomes, input records, measurement and counter-metrics, safeguards, eight delivery steps and acceptance criteria. Plans 001–006 retain unresolved titles and source mapping. Plans 007–050 use the supplied titles and explicitly labeled editorial proposals, except project 023 now also has a full user-supplied specification and implementation traceability. None is represented as a transcription of the linked document or a completed domain service.

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

The Google Docs retrieval attempts for the permit source and first foundational source were unsuccessful in the preparation environment. No Google Drive connection was selected. Therefore **the linked documents’ full contents are not included**, except that project 023’s full text was subsequently supplied directly by the user and is bundled under `portfolio/sources/023-user-specification.md`. It is not an authenticated fetch of the linked Google Doc. The application supports importing complete UTF-8 text, Markdown or JSON exports supplied by the owner. It does not convert PDF, Word or native Google Docs files.

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

**Outstanding project-specific work:** import and review the real source documents; confirm 001–006; replace or accept the proposed requirements; implement and test each confirmed domain workflow beyond the bounded project 009–018 and 023 simulations; obtain qualified acceptance and resolve licensing. This shared delivery application and synthetic labs are not substitutes for those 50 accepted domain implementations.

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

The [synthetic finance lab for project 018](FINANCE-LAB.md), at `/finance`, preserves category-specific signed entries, comparison histories and outcome notes. No payment, tax calculation or spending authorization occurs.

The [Project 023 justice observatory](JUSTICE-LAB.md), at `/justice`, adds the supplied specification, evidence-pinned gap analysis, caseflow strata, DTI intervals, checked remedies, metric contracts and human-authored research-role reviews. The bundled source can be explicitly imported into the source catalog; source review and real institutional acceptance are never automatic.

## Connected portfolio and collaboration rehearsal

The [connected initiative workspace](INITIATIVE-LAB.md), at `/initiative`, shows all 50 workstreams, source/completion gaps, the eleven existing synthetic prototypes and the shared methods. It adds explicit prerequisite dependencies, documented priorities, version-pinned safeguards and a checked staged pilot rehearsal based on the [supplied portfolio overview](sources/initiative-user-specification.md). It does not implement the outstanding domain services, fetch the linked Google Docs, identify a receiving office or send a collaboration proposal.

## Controllable use case

The [permit scenario control console](SCENARIO-CONTROLS.md), at `/scenarios`, provides all six workflow states, pause/resume/stop, valid stepping, a manual scenario clock, quality outcomes, presets, reset and append-only snapshot restore. It uses isolated scenario tables and does not change domain permit records, project acceptance or legal/execution holds.

## Project 019 procurement scenario

The [procurement and contract-delivery use case](PROCUREMENT-LAB.md), at `/scenarios?workflow=procurement`, adds nine controllable states, exact-revision acceptance by a distinct recorder identifier, correction invalidation, cancellation, presets and snapshot restore. Full project source review, real contract/competition data and qualified institutional acceptance remain outstanding. This remains a bounded synthetic domain prototype, not an institutionally completed project.

## Project 020 education scenario

The [education-service access and continuity use case](EDUCATION-LAB.md), at `/scenarios?workflow=education`, adds nine controllable states, service/follow-up revision checks, interruptions and withdrawal. It assesses no learning, eligibility or rankings. This remains a bounded synthetic prototype; source review and real institutional acceptance remain outstanding.

## Project 021 health-referral scenario

The [health-service referral and continuity use case](HEALTH-LAB.md), at `/scenarios?workflow=health`, adds eleven controllable states with fictional consent, handoffs/waiting, interruptions, fresh continuity checks and decline/withdrawal. No patient records, clinical decisions or outcomes are processed. This remains a bounded synthetic prototype; real source review, data governance and institutional acceptance remain outstanding.

## Project 022 readiness-exercise scenario

The [controlled readiness-exercise use case](EMERGENCY-LAB.md), at `/scenarios?workflow=emergency`, adds eleven states with separate readiness and corrective-action checks, response milestones, abort/cancel paths and replay/restore. Live dispatch and readiness certification remain false. There are now fifteen bounded synthetic domain prototypes (009–023); actual source review, safety rules and institutional acceptance remain outstanding.

## Project 023 scenario controls

The existing justice observatory now links an isolated [justice control use case](JUSTICE-CONTROLS.md), at `/scenarios?workflow=justice`, with fifteen states, separate notice/remedy/reentry checks, remand/rehearing loops and both remedy/reentry closure paths. No judicial, sentencing, bail or release decisions are made. This extends an existing prototype; the portfolio still has fifteen bounded synthetic domain prototypes, not institutionally accepted projects.
