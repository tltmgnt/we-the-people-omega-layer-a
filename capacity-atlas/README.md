# WE THE PEOPLE Ω Capacity Atlas

An interactive, browser-local planning interface that connects the A–E architecture to editable work estimates, dependencies, session time and interruption assumptions. The map is a synthetic working model, not a measure of intelligence or a clinical assessment of cognitive capacity.

## Run locally

With Python 3 and this repository downloaded, from the repository root:

```sh
python -m http.server 8767 --bind 127.0.0.1 --directory capacity-atlas/dist
```

Open <http://127.0.0.1:8767>. Keep the server running while using the interface. It serves static HTML, CSS and JavaScript with no build step, runtime package installation or external service calls. Serve the files over HTTP rather than opening `index.html` directly because the app uses JavaScript modules. Stop the server with Ctrl+C.

This is a source copy of the Capacity Atlas Site. It is separate from the Python/SQLite portfolio application in `layer-b/`; it does not read or update that database. Publishing this source does not alter the hosted Site's audience or deployment.

## Inputs and controls

| Control | Behavior |
| --- | --- |
| Example selector and Load example | Choose Balanced session, Fragmented day or Recovery plan. Loading replaces working history and baseline after confirmation when edits exist. Saved browser data changes only when explicitly saved. |
| Session length | 15–480 minutes in five-minute steps |
| Planned breaks | 0–120 minutes in five-minute steps |
| Expected interruptions | 0–20 whole interruptions |
| Recovery per interruption | 0–30 estimated minutes; a user assumption, not a biological constant |
| Apply session inputs | Commit slider settings to the current model; labels preview changes before applying |
| System / Focus / Constraints | Inspect the whole map, emphasize the selected node/direct connections, or fade completed work |
| Map nodes and labeled node buttons | Select an A–E work item for inspection and editing |
| Work item | Editable title of 1–100 characters |
| Estimated minutes | Whole minutes from 0 to 480 |
| Recorded minutes | Whole minutes from 0 through the item's estimate |
| Dependency checkboxes | Require selected prerequisite work to be completed; self-dependencies and cycles are rejected |
| Save node edits | Apply title, estimate, recorded time and dependencies; recheck affected states |
| Record focused work / Add minutes | Add positive whole minutes to the selected active task, bounded by its estimate and remaining usable time |
| Set baseline / Replace baseline | Freeze a comparison snapshot; replacement asks for confirmation |
| Restore | Copy an earlier core snapshot into a new history event without deleting intervening history or replacing the frozen baseline |
| Save in this browser | Explicitly save the session, baseline and history in this browser's local storage |
| Export / Import session | Download or load version-one JSON; imports are bounded to 2 MB, validated and confirmed before replacement |
| How this works | Explain the formulas, controls, limits and data handling |

## Capacity arithmetic

- Reserved recovery = expected interruptions × estimated recovery minutes.
- Usable time = max(0, session length − planned breaks − reserved recovery).
- Recorded work = sum of recorded node minutes.
- Time remaining = usable time − recorded work; it can be negative if assumptions are reduced after work was recorded.
- Remaining work = sum of unfinished estimates less recorded minutes.
- Planning margin = time remaining − remaining work. A negative value is a shortfall in this plan, not a personal ability score.

The balanced example starts with 120 session minutes, 15 break minutes and 2 interruptions at 5 recovery minutes: 95 usable minutes against 95 estimated work minutes. Increasing interruptions to four reduces usable time and planning margin by 10 minutes. These are descriptive changes in supplied assumptions, not causal evidence of improved cognition or institutional outcomes.

## Every work state

| State | Available transitions |
| --- | --- |
| QUEUED | Start → ACTIVE; Block → BLOCKED |
| ACTIVE | Pause → PAUSED; Block → BLOCKED; Complete → COMPLETED |
| PAUSED | Resume → ACTIVE; Block → BLOCKED |
| BLOCKED | Unblock → QUEUED |
| COMPLETED | Reopen → QUEUED |

Start/resume require completed prerequisites and only one active task at a time. When unfinished minutes remain, there must also be usable session time left. Unblock does not bypass prerequisites. Complete requires recorded minutes to equal the estimate; revise the estimate deliberately if work finished earlier. Reopen retains recorded minutes and blocks dependent active/completed work for rechecking. Editing dependencies or estimates also rechecks affected states. There is no background timer or automatic work execution.

The default dependencies are A → B, B and D → C, and C and D → E. D can begin independently. These editable fictional dependencies are not a legal interpretation of the five-layer architecture.

## Persistence and limits

History is capped at 200 events. Export and load a new example at the limit. Saving is explicit, browser-local and not synchronized between devices. Local history and imported data are user assertions, not an authenticated audit ledger. Browser storage can be unavailable or cleared; keep an export when the record matters.

Use fictional, non-sensitive entries. Review exported text before sharing. The app does not provide production identity verification, protected-data authorization, real service control or qualified legal acceptance. Execution remains unauthorized, and this planning interface does not clear the portfolio's Layer A review holds.

## Verification

With Node.js 22, from `capacity-atlas/`:

```sh
node --test model.test.mjs
node --check dist/app.mjs
```

The model tests cover budget arithmetic, invalid transitions, dependency and single-focus checks, reopening downstream work, cycles, malformed imports, work limits and frozen-record independence.

The GitHub workflow also runs `browser-smoke.cjs` against an isolated local static server. It checks real interface interactions, failures, baseline comparison, explicit save/reload, export/import, restore and mobile layout. Browser tooling is a development dependency only; see [the workflow](../.github/workflows/validate-capacity-atlas.yml) for its pinned setup.

[Five-layer architecture](../Docs/Architecture/README.md) · [Portfolio application](../layer-b/portfolio/APPLICATION.md) · [C/D/E evidence and learning workspaces](../layer-b/portfolio/LAYER-WORKSPACES.md)
