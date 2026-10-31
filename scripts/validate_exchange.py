"""Validate a proposed synthetic exchange and its pinned local references."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

from scripts.validate_review import ROOT, validator as review_validator


class ExchangeError(ValueError):
    pass


def read_pinned(reference, root):
    root = root.resolve()
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ExchangeError("references must be repository-relative and cannot traverse parents")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ExchangeError("reference resolves outside the repository")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ExchangeError(f"pinned content changed: {reference['path']}")
    return json.loads(raw)


def check_exchange(exchange, root=ROOT):
    schema = json.loads((ROOT / "schemas/cross-layer-exchange.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(exchange))
    if errors:
        raise ExchangeError(errors[0].message)
    proposal = exchange["layer_b"]["proposal_id"]
    for layer in ["layer_c", "layer_a_ref", "layer_d"]:
        if exchange[layer]["proposal_id"] != proposal:
            raise ExchangeError(f"{layer} proposal_id does not match Layer B")
    reference = exchange["layer_a_ref"]
    review = read_pinned(reference, root)
    errors = list(review_validator().iter_errors(review))
    if errors:
        raise ExchangeError(f"invalid Layer A record: {errors[0].message}")
    for field in ["review_id", "proposal_id", "schema_version", "revision"]:
        if reference[field] != review[field]:
            raise ExchangeError(f"Layer A {field} does not match pinned record")
    evidence = exchange["layer_d"]
    manifest = read_pinned(evidence["manifest_ref"], root)
    if not isinstance(manifest, dict) or manifest.get("pilot_id") != review["review_id"]:
        raise ExchangeError("manifest does not identify the pinned pilot review")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ExchangeError("manifest must contain source entries")
    identifiers = []
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("evidence_id"), str):
            raise ExchangeError("invalid manifest source entry")
        identifiers.append(source["evidence_id"])
    if len(set(identifiers)) != len(identifiers):
        raise ExchangeError("duplicate manifest evidence IDs")
    supplied = set(evidence["evidence_ids"])
    if not supplied.issubset(identifiers):
        raise ExchangeError("Layer D references evidence absent from the manifest")
    if not set(review["evidence_ids"]).issubset(supplied):
        raise ExchangeError("Layer D omits evidence referenced by Layer A")
    # This initial synthetic contract requires nonempty Layer D uncertainties.
    # It intentionally has no ready/approved state or operational authorization.
    return review["review_status"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exchange", type=Path)
    parser.add_argument("--require-ready", action="store_true",
                        help="exit 2 for this deliberately blocked synthetic exchange")
    args = parser.parse_args(argv)
    try:
        exchange = json.loads(args.exchange.read_text(encoding="utf-8"))
        status = check_exchange(exchange)
    except (OSError, ValueError) as exc:
        print(f"INVALID EXCHANGE: {exc}", file=sys.stderr)
        return 1
    print(f"VALID EXCHANGE; BLOCKED (Layer A: {status}; unresolved Layer D uncertainty); no implementation authorization")
    return 2 if args.require_ready else 0


if __name__ == "__main__":
    sys.exit(main())
