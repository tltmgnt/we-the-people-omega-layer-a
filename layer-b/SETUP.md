# Repository setup and acceptance

## Current repository

Layer B is published inside the public [Layer A repository](https://github.com/tltmgnt/we-the-people-omega-layer-a), under `layer-b/`. The owner selected this destination for the starter import.

[PR #7](https://github.com/tltmgnt/we-the-people-omega-layer-a/pull/7) imported the 42-file starter and was merged on 2026-10-31. The original package was prepared for a standalone Layer B repository; this import uses a subdirectory instead.

## Work locally

From a checkout of the repository, enter the Layer B directory before running its commands:

```sh
cd layer-b
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m scripts.validate_packet examples/permit/operational-review.json
python -m scripts.validate_packet --require-ready examples/permit/operational-review.json
```

Use Python 3.12. The tests and ordinary packet validation should exit 0. The synthetic packet remains BLOCKED; `--require-ready` should exit 2.

The active Layer B workflow is [validate-layer-b.yml](../.github/workflows/validate-layer-b.yml). Files under `layer-b/.github/` are preserved starter templates; GitHub does not activate them from that location. Layer A retains its own workflow and root-level tooling.

See [validation evidence](VALIDATION.md) for the merged import's passing CI runs. No release or operational deployment has been performed by this import.

## Acceptance checklist

- [x] Exact repository and public visibility chosen by owner.
- [ ] Code/docs/Layer A snapshot license coverage explicitly authorized.
- [ ] Six domains and thirteen supplied framework sections mapped in ORIGIN.md and accepted by reviewers.
- [ ] Domain, financial terminology and gate content reviewed by qualified people.
- [x] Tests and CI pass on the merged import commit recorded in VALIDATION.md.
- [x] Permit example remains synthetic, unmeasured and blocked.
- [ ] Confirm any future contribution excludes protected institutional/personnel/vendor records and credentials.
- [ ] Qualified review and release criteria completed before claiming readiness.
- [ ] Release, remote access and consequential-action roles separately authorized.

## Next owner decisions

1. Resolve [license selection](LICENSE-SELECTION.md), including the vendored Layer A snapshot.
2. Select a bounded proposed function and accountable owner using the [roadmap](ROADMAP.md).
3. Identify qualified reviewers and record unresolved authority and data-access questions.

Public repository visibility and structural validation do not establish jurisdiction-specific compliance or authorize a real pilot. There are no live data connectors or operational permissions.
