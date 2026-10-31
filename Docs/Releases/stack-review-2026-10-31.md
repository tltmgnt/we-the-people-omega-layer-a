# PR stack review — 2026-10-31

## Scope and outcome

Reviewed the combined implementation from PRs 1–5 through preparation head
efbfa7d762eca9e887e21c57280bb972bf49419c: schemas, validators, synthetic fixtures,
tests, CI, domain guidance, integration documentation and release criteria.
This is a code and documentation review, not a qualified legal review or a security certification.

Found and fixed one input-parsing ambiguity. The amended suite passes 21 test methods.
Examples retain their intended blocked outcomes. No merge, license selection, tag,
release publication or institutional authorization was performed.

## Finding and correction

| Finding | Reproduction and consequence | Correction |
| --- | --- | --- |
| Duplicate object keys silently accepted | A record containing two review_status keys was accepted with exit 0 because Python retained the last value. Different readers could interpret the same record differently. | Shared strict JSON loader rejects duplicate keys at any depth before schema validation. |
| Related nonstandard parser acceptance | Python's default loader also accepts NaN and positive/negative Infinity outside standard JSON syntax. | Reject these constants in the same loader, including pinned review and source-manifest JSON. |

CLI invalid-input exit remains 1; the review schema and exchange schema versions remain
0.1.0. No supported schema fields or statuses change. Pinned file bytes and hashes for
the unchanged example remain intact. Callers passing already-parsed dictionaries to
check_exchange must ensure that their own JSON parser enforces the same input policy;
duplicates cannot be recovered after parsing.

Regression checks cover record and exchange CLI inputs, nested duplicates, all three
nonstandard constants, matching-hash pinned malformed JSON and invalid UTF-8 bytes.

## Other reviewed behavior

- Readiness is distinct from structural validity; missing legal authority and unresolved
  blockers keep the synthetic review packet held.
- Exchange references bind proposal and review identity, revision, schema version and
  exact bytes. Evidence IDs must resolve in the pinned manifest and cover the A record.
- Repository-bound references reject parent traversal, absolute paths and escaping symlinks.
- The synthetic exchange deliberately has no ready state; D uncertainty remains explicit.
- All seven domain documents have review questions, evidence requests and escalation
  instructions. Their legal applicability and substantive completeness still require
  qualified human assessment.
- CI runs tests and structural examples. Negative tests exercise readiness exit codes.
  Green CI does not establish reviewer identity, legal sufficiency or release approval.
- Release preparation documents preserve pending licensing, reviewer assignment and
  final-main evidence rather than treating preparatory checks as completed acceptance.

## Validation

On the amended local tree using Python 3.12:

| Check | Result |
| --- | --- |
| Unit/integration suite | 21 methods pass |
| Original and both pilot records | Exit 0, VALID; BLOCKED |
| Pilot readiness check | Exit 2, BLOCKED |
| Synthetic exchange | Exit 0, VALID EXCHANGE; BLOCKED |
| Exchange readiness check | Exit 2, BLOCKED |
| Local Markdown file links | Resolve |

PR 5 push and pull-request CI runs were successful when this review began:
[push/PR run](https://github.com/tltmgnt/we-the-people-omega-layer-a/actions/runs/41222299235)
and [companion run](https://github.com/tltmgnt/we-the-people-omega-layer-a/actions/runs/41222302543).
These earlier runs do not verify the parser fix or the eventual final main commit.
Consult the parser-fix PR's checks for its remote results.

## Remaining release work

1. Review and merge the stack in predecessor order, including the parser-fix PR; retarget
   descendants and verify their diffs and checks as described in the release procedure.
2. Obtain an explicit owner license decision and commit the authorized license coverage
   before inviting public reuse.
3. Obtain and record qualified domain/gate content review and disposition of findings.
4. Populate the release ledger and rerun checks on the exact final main commit.
5. Obtain the maintainer's approval before creating the release tag and publishing notes.

The known production limits remain those already documented: no authenticated reviewer
provenance, authoritative cross-repository freshness policy, general historical-transition
enforcement or completed jurisdiction-specific human-reviewed pilot.
