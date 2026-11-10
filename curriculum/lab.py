"""Offline curriculum answer key. Synthetic checks, never operational approval."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
for base in (ROOT, ROOT / "src", ROOT / "layer-b"):
    sys.path.insert(0, str(base))
CASES = []

def check(name, actual, expected):
    passed = actual == expected
    CASES.append({"case": name, "actual": actual, "expected": expected, "passed": passed})
    if not passed:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")

def rejects(name, call, error=ValueError):
    try:
        call()
    except error:
        check(name, error.__name__, error.__name__)
    else:
        raise AssertionError(f"{name}: expected {error.__name__}")

def sample(path):
    return json.loads((ROOT / path).read_text())

def leaf(path):
    # Load a reviewed standalone module without importing unrelated applications.
    spec = importlib.util.spec_from_file_location("curriculum_subject", ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run():
    from contextlib import redirect_stdout
    import io
    module = leaf("scripts/validate_review.py")
    data = sample("example-review.json")
    check("synthetic review fits schema", module.validator().is_valid(data), True)
    with redirect_stdout(io.StringIO()):
        check("valid record need not be ready", module.main([str(ROOT/"example-review.json"),"--require-ready"]), 2)
    rejects("duplicate review status is ambiguous JSON", lambda: module.load_json('{"review_status":"DRAFT","review_status":"READY_FOR_HUMAN_DECISION"}'))
    rejects("nonstandard NaN rejected", lambda: module.load_json('{"revision":NaN}'))
    bad = copy.deepcopy(data); bad["review_status"] = "READY_FOR_HUMAN_DECISION"
    check("changing label alone does not satisfy readiness", module.validator().is_valid(bad), False)

if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--verify"]):
        raise SystemExit("Usage: python curriculum/lab.py [--verify]")
    run()
    report = {"schema_version": 1, "status": "PASS", "case_count": len(CASES),
              "cases": CASES, "scope": "Synthetic curriculum checks only"}
    if sys.argv[1:] == ["--verify"]:
        expected = json.loads((Path(__file__).parent / "expected.json").read_text())
        if report != expected:
            raise AssertionError("Observed answers differ from curriculum/expected.json")
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
