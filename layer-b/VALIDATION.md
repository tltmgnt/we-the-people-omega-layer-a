# Preparation and import validation — 2026-10-31

## Portfolio application follow-up

Local verification of the shared portfolio application: all 20 Layer B tests pass (13 existing packet tests and 7 new application tests). All 21 root Layer A tests also pass. JavaScript syntax checking passes. A local browser executable was unavailable and its download failed, so local visual verification is not claimed. The application browser smoke check is included for GitHub CI.

Application tests cover all 50 IDs and generated plans, full-text source preservation/hashing/versioning, user-attributed review records, persisted edits, stale-write/review rejection, completion evidence, changed-source/scope invalidation, HTTP mutation/export, loopback origin checks and restorable SQLite backup. No complete domain-project implementation or external source-document import is claimed.

## Merged starter import evidence

The starter was prepared and tested locally with Python 3.12, then imported through [PR #7](https://github.com/tltmgnt/we-the-people-omega-layer-a/pull/7).

Both workflows passed on merged import commit `eb2a3df04b7a585b8bdd373b3059c108a085bee1`:
- [Layer B validation](https://github.com/tltmgnt/we-the-people-omega-layer-a/actions/runs/41225990939)
- [Layer A review-record validation](https://github.com/tltmgnt/we-the-people-omega-layer-a/actions/runs/41225990941)

This evidence applies to that commit. Later changes require their own checks. The Layer B workflow runs from `layer-b/` and checks the expected blocked readiness exit code.

| Check | Result |
| --- | --- |
| Unit/integration tests | 13 methods pass, including required-field and negative-input subtests |
| Synthetic permit packet | Valid structure and reference consistency; BLOCKED |
| Permit --require-ready | Exit 2; BLOCKED |
| Documentation links | All local Markdown file links resolve |
| Upstream A schema | Unchanged snapshot at the commit recorded in vendor/layer-a/UPSTREAM.md |
| Portfolio | 50 stable numbered slots, unresolved assignments retained, five layer links recorded |

Tests cover duplicate JSON keys/constants, required fields, versions/types, all-six-domain
screening, reference identity/revision/hash, evidence membership, duplicate record IDs,
path traversal and escaping symlinks, Layer A hold enforcement, attribution requirements,
invalid timestamps/UTF-8, null unmeasured values and preserved portfolio unknowns.

The positive readiness test uses synthetic in-memory/temporary reviewer assertions only;
it does not alter the delivered blocked packet or represent a completed human review.

Pending owner/institution work: licensing, qualified
content review, program/jurisdiction/owner selection, lawful data access and any actual
collaboration or intervention. See SETUP.md and ROADMAP.md.
