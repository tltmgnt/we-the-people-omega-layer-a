# WE THE PEOPLE Ω — Five-Layer Architecture A–E

WE THE PEOPLE Ω is a civic systems research, education, evaluation and institutional improvement initiative. Its five connected layers examine lawful authority, government operations, human outcomes, evidence and controlled improvement.

This repository contains the **A–E architecture, a 50-slot project portfolio, and controllable synthetic software prototypes**. The repository retains its original `we-the-people-omega-layer-a` name; it now documents all five layers. The shared local application, including the C/D/E workspaces, lives under `layer-b/`.

## Start here

- [Five-layer architecture index](Docs/Architecture/README.md)
- [Run the portfolio application](layer-b/portfolio/APPLICATION.md)
- [State controls for all 44 defined workstreams](layer-b/portfolio/CONTROLLED-PORTFOLIO.md)
- [Dedicated C/D/E workspaces and worked example](layer-b/portfolio/LAYER-WORKSPACES.md)
- [All 50 project slots and six definition holds](layer-b/portfolio/CONTROL-COVERAGE.md)
- [50 numbered project plans](layer-b/portfolio/plans/README.md)

## The five-layer architecture

| Layer | Purpose | Repository entry point |
| --- | --- | --- |
| **A — Constitutional Legitimacy** | Establish authority, rights, jurisdiction, democratic accountability and ethical boundaries. | [Layer A architecture](Docs/Architecture/layers/A-constitutional-legitimacy.md) |
| **B — Government Operations** | Examine how resources, people, information and institutional processes become reliable services. | [Layer B architecture](Docs/Architecture/layers/B-government-operations.md) |
| **C — Human and Community Outcomes** | Evaluate meaningful effects on people and communities using defined outcomes and counter-measures. | [Layer C architecture](Docs/Architecture/layers/C-human-community-outcomes.md) |
| **D — Intelligence and Evidence** | Make sources, analytical assumptions, uncertainty, validation and correction traceable. | [Layer D architecture](Docs/Architecture/layers/D-intelligence-evidence.md) |
| **E — Transformation and Institutional Learning** | Connect diagnosis to controlled pilots, review, transition, corrective action and learning. | [Layer E architecture](Docs/Architecture/layers/E-transformation-learning.md) |

### Layer A — Constitutional Legitimacy

Layer A addresses constitutional rights, civil liberties, rule of law, elections, courts, government ethics, federalism, intergovernmental authority and Tribal sovereignty. It asks who may act, under which authority, with which protections and routes to challenge error.

The repository provides review architecture, A1–A7 domain prompts, a review schema, synthetic review examples and structural validation. The local rights lab records evidence, questions and challenges. These tools do not establish qualified legal review or institutional permission.

[Detailed architecture](Docs/Architecture/Layer-a-overview.md) · [A1–A7 domains](Docs/Domains/README.md) · [Review gate](Docs/Assurance/review-gate.md) · [Rights lab](layer-b/portfolio/RIGHTS-LAB.md)

### Layer B — Government Operations

Layer B examines institutional processes, budgets, procurement, workforce capacity, records, public works and essential services. It maps how lawful authority and resources move through handoffs, queues, decisions, corrections and service delivery.

The local application includes project definitions and owners, source import/review, work evidence, domain labs and synthetic scenario controls. Dedicated labs cover permits, maintenance, sanitation, transit, housing, public access, utilities, rights, election services, finance and justice. The shared controller provides synthetic use cases for all 44 defined workstreams.

[Detailed architecture](layer-b/docs/Architecture/layer-b-overview.md) · [Application guide](layer-b/portfolio/APPLICATION.md) · [Scenario controls](layer-b/portfolio/CONTROLLED-PORTFOLIO.md) · [Connected initiative workspace](layer-b/portfolio/INITIATIVE-LAB.md)

### Layer C — Human and Community Outcomes

Layer C examines education, healthcare, housing, food security, employment, public safety, mobility, environmental quality, civic participation and community well-being. Its central question is whether services produce meaningful outcomes, with attention to access, distribution, uncertainty and unintended effects.

The dedicated synthetic workspace defines outcome studies with units, cohorts, exclusions, uncertainty, owners and counter-measures. It records baseline/follow-up observations pinned to evidence revisions and requires separate checks. Descriptive deltas and rehearsal readiness are withheld when required observations, checks or counter-measures are missing, windows overlap, or evidence is stale. These comparisons do not establish causal effects or verified human benefit.

[Layer C architecture](Docs/Architecture/layers/C-human-community-outcomes.md) · [C/D/E workspace guide](layer-b/portfolio/LAYER-WORKSPACES.md) · [Scorecard proposal](layer-b/docs/Methods/scorecard.md)

### Layer D — Intelligence and Evidence

Layer D provides the shared research and analytical foundation: Topological Gap Analysis Ω, DTI Ω temporal-capacity analysis, the proposed HedgeOps Ω decision-support architecture, data provenance and quality, causal-evaluation design, AI governance, uncertainty and independent validation.

The dedicated synthetic evidence registry retains exact text, SHA-256 revisions, origin, confidence A/B/C assertions, limitations and separate revision checks. Other tools preserve source snapshots, frozen scenario comparisons and selected review bundles. Hashes and local reviewer identifiers do not authenticate source truth or qualified acceptance. Method documentation and simulated role notes are not executed or benchmarked multi-agent analysis.

[Layer D architecture](Docs/Architecture/layers/D-intelligence-evidence.md) · [Evidence workspace](layer-b/portfolio/LAYER-WORKSPACES.md) · [Topological analysis](layer-b/docs/Methods/topological-gap-analysis.md) · [DTI](layer-b/docs/Methods/temporal-burden.md) · [HedgeOps](layer-b/docs/Governance/hedgeops.md)

### Layer E — Transformation and Institutional Learning

Layer E connects findings to controlled pilots, performance reporting, independent review, transition management, leadership, corrective action, adoption and continuous improvement.

The dedicated synthetic workspace records a rehearsal plan with scope, owner, resources, service continuity and rollback arrangements linked to C studies. Its phases are DRAFT → DESIGNED → BASELINE_RECORDED → REHEARSAL_RECORDED → EVALUATION_RECORDED → LEARNING_RECORDED. Forward progression requires the applicable current separate checks; rehearsal and later phases also require complete current checked C outcome pairs. Source or outcome changes invalidate prior context. REOPEN and ROLLBACK retain history. These are local learning records, not actual institutional transitions or adoption evidence.

[Layer E architecture](Docs/Architecture/layers/E-transformation-learning.md) · [Phase controls and recovery](layer-b/portfolio/LAYER-WORKSPACES.md) · [Collaboration and pilot design](layer-b/docs/Collaboration/concept-and-pilot.md)

## How the layers connect

Establish legitimacy → understand operations → measure human outcomes → validate evidence → test separately authorized improvements → verify results → institutionalize learning.

The cycle includes feedback: evidence can challenge an outcome claim, a pilot can reveal an operational gap, and an unresolved authority or rights question returns to Layer A. Operational performance never overrides a legal or rights hold.

In the dedicated local workspaces, **D evidence revisions → C pinned observations → E context-pinned rehearsal records**. The B scenario controller has a separate p050 capstone mechanism that attaches exact snapshots from eligible source scenarios. These mechanisms are explicit local dependencies; there is no automatic integration that certifies the entire institutional system.

[Cross-layer alignment](layer-b/docs/Architecture/five-layer-alignment.md) · [Versioned synthetic exchange](examples/cross-layer/README.md) · [Capstone controls](layer-b/portfolio/controlled-use-cases/050.md)

## State-by-state controls and edits

**Every declared scenario state can be inspected; available edits and controls depend on that state's rules.** The software rejects invalid transitions rather than allowing arbitrary state forcing.

- **Workflow and time:** step through valid transitions; pause, stop or resume where permitted; explicitly advance fictional time; inspect presets and prior snapshots.
- **Revisions and corrections:** edit project definitions, import source revisions and append corrected observations. Changed project requirements reset dependent work assertions; dependency invalidation follows each workspace's documented contract.
- **Review and recovery:** retain failed and passing checks, use correction loops, reopen eligible records, and restore scenario snapshots into new history events.
- **Evidence freshness:** detect changed source scenarios or revised evidence, withhold affected results, and require current references/checks before applicable progression.
- **Immutable contracts:** C study and E trial definitions require a new ID when changed. Evidence revisions, observation replacements and history remain attributable; correction does not silently rewrite the past.
- **Fixed boundaries:** local passes do not clear `LEGAL_REVIEW_REQUIRED` or change `execution_authorized=false`.

Controls differ between the shared scenario controller and individual labs. Consult their state maps and handoffs for terminal states, role separation, version checks and recovery conditions.

[Permit state example](layer-b/portfolio/SCENARIO-CONTROLS.md) · [All defined workflow controls](layer-b/portfolio/CONTROLLED-PORTFOLIO.md) · [C/D/E state table](layer-b/portfolio/LAYER-WORKSPACES.md)

## The 50-project portfolio

Projects are connected research and implementation workstreams, not 50 independently accepted operational systems.

- **001–006:** foundational project titles, scopes and source mappings remain unresolved; definition holds are preserved.
- **007–040:** defined civic capacity, policy and domain workstreams, including Project 023, Courts, Justice and Corrections.
- **041–050:** shared curriculum, systems methods, evidence, temporal capacity, decision intelligence, transition, rights assurance, validation, leadership and capstone integration.

All **44 defined workstreams, 007–050**, have controllable synthetic scenarios. The demo loader creates inspectable fictional examples without overwriting operator changes. The register contains all 50 slots and preserves the six unresolved definitions.

[Project register](layer-b/portfolio/project-register.json) · [Coverage](layer-b/portfolio/CONTROL-COVERAGE.md) · [Demo loader](layer-b/portfolio/DEMO-LOADER.md) · [Project 023 specification and lab](layer-b/portfolio/JUSTICE-LAB.md)

## Run the local application

With Python 3.12, from the repository root:

```sh
cd layer-b
python -m civic_portfolio init
python -m civic_portfolio serve --port 8765
```

Open <http://127.0.0.1:8765>. The application binds to loopback and uses the Python standard library at runtime. It is a local single-workspace prototype, not an authenticated public internet service.

| Local page | Workspace |
| --- | --- |
| `/` | Portfolio, project definitions, sources and work evidence |
| `/rights` | Layer A rights questions and evidence |
| `/scenarios` | Shared synthetic workflow controls and demo batches |
| `/layers` | Dedicated C outcomes, D evidence and E learning records |
| `/justice` | Project 023 research and pilot prototype |
| `/compare-scenarios` | Frozen baseline/alternative scenario comparisons |
| `/review-bundles` | Selected scenario snapshots and verification ZIP |

Workspace JSON export and SQLite backup preserve entered records. Selected scenario ZIPs contain only their documented selection and dependencies; **they do not include the separate C/D/E workspace records**. Review scope and entered text before sharing.

[Export and backup instructions](layer-b/portfolio/APPLICATION.md) · [Comparison guide](layer-b/portfolio/SCENARIO-COMPARISONS.md) · [Review bundle scope and verifier](layer-b/portfolio/REVIEW-BUNDLES.md)

## Validation

Run the Layer A review checks from the **repository root**:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/validate_review.py example-review.json
```

Run the application and operational packet checks from **`layer-b/`**:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m scripts.validate_packet examples/permit/operational-review.json
```

The example review and operational packet pass structural validation while remaining **BLOCKED**. Structural validity does not establish legal sufficiency, reviewer authority or execution permission. CI also runs a portfolio browser walkthrough covering controls, evidence holds, recovery, persistence and mobile layout.

[Root validation workflow](.github/workflows/validate.yml) · [Application and browser workflow](.github/workflows/validate-layer-b.yml) · [Review gate and exit codes](Docs/Assurance/review-gate.md)

## Current implementation and acceptance status

All five layers are represented in the architecture and linked repository material. A has review scaffolding; B has operations documentation and local prototypes; C, D and E have dedicated synthetic workspaces in the shared application. This is a bounded research and software prototype, not a completed government operating system.

Full linked Google Docs have not been imported or reviewed as complete requirements. Project 023's full user-supplied text is preserved separately; it is not an authenticated fetch of its linked document. Final definitions for 001–006, real data evaluation, method benchmarking, qualified legal/security/professional review, institutional acceptance and any live deployment authorization remain outstanding.

The proposed combined methodology is not claimed to be a validated universal standard. A recorded completion, passing test, confidence label or checked rehearsal does not by itself establish actual human benefit or institutional adoption.

## Further documentation

- [Review JSON Schema](schemas/review-record.schema.json) and [hypothetical review record](example-review.json)
- [Synthetic benefits-process example](pilots/benefits-process/README.md)
- [Cross-layer integration](cross-layer-integration.md)
- [Contribution guidance](CONTRIBUTING.md) and [changelog](CHANGELOG.md)
- [Roadmap](ROADMAP.md) and [Layer A alpha release criteria](Docs/Releases/0.2.0-alpha.md)
- [License selection status](LICENSE-SELECTION.md)

### Foundational reference starting points

- [U.S. Constitution — National Archives](https://www.archives.gov/founding-docs/constitution)
- [Bill of Rights — National Archives](https://www.archives.gov/founding-docs/bill-of-rights)
- [Constitution Annotated — Congress](https://constitution.congress.gov/)
- [U.S. Election Assistance Commission](https://www.eac.gov/)
- [Bureau of Indian Affairs](https://www.bia.gov/)

These are research starting points, not exhaustive controlling authority. Check current applicable constitutional text, statutes, treaties, Tribal law, judicial decisions and jurisdiction-specific requirements before relying on a legal conclusion.
