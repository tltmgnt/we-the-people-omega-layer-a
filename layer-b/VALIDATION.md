# Preparation validation — 2026-10-31

Prepared locally with Python 3.12. No GitHub repository was created and no remote CI run
is claimed. The included workflow will run after import into an appropriate repository.

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

Pending owner/institution work: target repository and visibility, licensing, qualified
content review, program/jurisdiction/owner selection, lawful data access and any actual
collaboration or intervention. See SETUP.md and ROADMAP.md.
