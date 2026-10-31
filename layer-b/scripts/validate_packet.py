"""Validate a local Layer B packet; structural success never authorizes execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from rfc3339_validator import validate_rfc3339

ROOT = Path(__file__).resolve().parents[1]


def load_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject(value):
        raise ValueError(f"invalid JSON constant: {value}")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def schema_validator(path):
    schema = load_json(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    checker = FormatChecker()
    # Register explicitly so the time contract never silently becomes optional.
    checker.checks("date-time")(
        lambda value: not isinstance(value, str) or validate_rfc3339(value.upper()))
    return Draft202012Validator(schema, format_checker=checker)


def require_valid(record, schema_path):
    errors = sorted(schema_validator(schema_path).iter_errors(record),
                    key=lambda error: str(list(error.path)))
    if errors:
        error = errors[0]
        location = ".".join(map(str, error.path)) or "$"
        raise ValueError(f"{location}: {error.message}")


def read_pinned(reference, root):
    root = root.resolve()
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("reference must be repository-relative without parent traversal")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("reference escapes repository")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError(f"pinned content changed: {reference['path']}")
    return raw


def check_packet(record, root=ROOT):
    require_valid(record, ROOT / "schemas/operational-review.schema.json")
    reference = record["layer_a_ref"]
    review = load_json(read_pinned(reference, root).decode("utf-8"))
    require_valid(review, ROOT / "vendor/layer-a/review-record.schema.json")
    for field in ["review_id", "revision", "schema_version"]:
        if review[field] != reference[field]:
            raise ValueError(f"Layer A {field} mismatch")
    if review["proposal_id"] != record["proposal_id"]:
        raise ValueError("Layer A proposal_id mismatch")
    sources = {}
    for evidence in record["evidence"]:
        identifier = evidence["evidence_id"]
        if identifier in sources:
            raise ValueError(f"duplicate evidence ID: {identifier}")
        read_pinned(evidence, root)
        sources[identifier] = evidence
    for collection, field in [("metrics", "metric_id"), ("gaps", "gap_id")]:
        ids = [item[field] for item in record[collection]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate {field}")
    for metric in record["metrics"]:
        if metric["source_id"] not in sources:
            raise ValueError("metric source_id does not resolve")
    for gap in record["gaps"]:
        identifiers = gap["evidence_ids"] + gap.get("verification_evidence_ids", [])
        if not set(identifiers).issubset(sources):
            raise ValueError("gap evidence does not resolve")
    if not set(review["evidence_ids"]).issubset(sources):
        raise ValueError("Layer A evidence does not resolve")
    ready = record["review_status"] == "READY_FOR_HUMAN_DECISION"
    if ready and review["review_status"] != "READY_FOR_HUMAN_DECISION":
        raise ValueError("Layer B readiness cannot override Layer A hold")
    return ready, review["review_status"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        record = load_json(args.record.read_text(encoding="utf-8"))
        ready, status = check_packet(record)
    except (OSError, ValueError) as error:
        print(f"INVALID PACKET: {error}", file=sys.stderr)
        return 1
    gate = "READY FOR HUMAN DECISION" if ready else "BLOCKED"
    print(f"VALID PACKET; {gate}; Layer A: {status}; no execution authorization")
    return 2 if args.require_ready and not ready else 0


if __name__ == "__main__":
    sys.exit(main())
