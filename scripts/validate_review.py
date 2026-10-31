"""Validate record structure; optionally require readiness for a human decision."""
import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def validator():
    schema = json.loads((ROOT / "schemas/review-record.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+", type=Path)
    parser.add_argument("--require-ready", action="store_true",
                        help="exit 2 for valid records not ready for a human decision")
    args = parser.parse_args(argv)
    check = validator()
    invalid = False
    blocked = False
    for path in args.records:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{path}: INVALID: {exc}", file=sys.stderr)
            invalid = True
            continue
        errors = sorted(check.iter_errors(record), key=lambda e: str(list(e.path)))
        if errors:
            invalid = True
            for error in errors:
                location = ".".join(map(str, error.path)) or "$"
                print(f"{path}: INVALID at {location}: {error.message}", file=sys.stderr)
            continue
        ready = record["review_status"] == "READY_FOR_HUMAN_DECISION"
        blocked |= not ready
        gate = "READY FOR HUMAN DECISION" if ready else "BLOCKED"
        print(f'{path}: VALID; {gate} ({record["review_status"]}); no implementation authorization')
    return 1 if invalid else 2 if args.require_ready and blocked else 0


if __name__ == "__main__":
    sys.exit(main())
