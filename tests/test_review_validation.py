import copy
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest

from scripts.validate_review import ROOT, load_json, main, validator


class ReviewValidationTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / "example-review.json").read_text())
        self.check = validator()

    def test_existing_example_valid_but_blocked(self):
        self.assertEqual(list(self.check.iter_errors(self.record)), [])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(ROOT / "example-review.json")]), 0)
            self.assertEqual(main(["--require-ready", str(ROOT / "example-review.json")]), 2)

    def test_every_required_field_is_enforced(self):
        for field in self.record:
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                del record[field]
                self.assertFalse(self.check.is_valid(record))

    def test_invalid_values(self):
        for field, value in [
            ("review_status", "APPROVED"), ("schema_version", "9.0.0"),
            ("revision", 0), ("revision", True), ("proposal_id", "  "),
            ("jurisdictions", []), ("rights_affected", [""]),
            ("evidence_ids", "source"), ("unexpected", "field"),
            ("reviewed_at", "yesterday"),
        ]:
            with self.subTest(field=field, value=value):
                record = copy.deepcopy(self.record)
                record[field] = value
                self.assertFalse(self.check.is_valid(record))

    def test_ambiguous_and_nonstandard_json_is_rejected(self):
        duplicate = '{"review_status":"DRAFT",' + json.dumps(self.record)[1:]
        values = [
            duplicate, '{"nested":{"id":"first","id":"last"}}',
            '{"revision":NaN}', '{"revision":Infinity}', '{"revision":-Infinity}',
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            for value in values:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        load_json(value)
                    path.write_text(value)
                    with redirect_stderr(io.StringIO()):
                        self.assertEqual(main(["--require-ready", str(path)]), 1)

    def ready_record(self):
        record = copy.deepcopy(self.record)
        record.update(review_status="READY_FOR_HUMAN_DECISION",
                      reviewer_id="SYNTHETIC-REVIEWER", reviewed_at="2026-10-31T12:00:00Z",
                      jurisdictions=["Synthetic jurisdiction"],
                      legal_authorities=["Synthetic authority reference"],
                      evidence_ids=["SYNTHETIC-EVIDENCE-001"], unresolved_questions=[],
                      conditions=[], jurisdictional_limitations=[])
        return record

    def test_changing_status_does_not_bypass_unresolved_review(self):
        self.record["review_status"] = "READY_FOR_HUMAN_DECISION"
        self.assertFalse(self.check.is_valid(self.record))

    def test_ready_requires_attribution_sources_and_no_blockers(self):
        ready = self.ready_record()
        self.assertTrue(self.check.is_valid(ready))
        for field, value in [
            ("reviewer_id", ""), ("reviewed_at", "invalid"),
            ("legal_authorities", []), ("evidence_ids", []),
            ("unresolved_questions", ["Unresolved authority"]),
            ("conditions", ["Pending verification"]),
            ("jurisdictional_limitations", ["Authority uncertain"]),
        ]:
            with self.subTest(field=field):
                record = copy.deepcopy(ready)
                record[field] = value
                self.assertFalse(self.check.is_valid(record))
        for field in ["reviewer_id", "reviewed_at"]:
            record = copy.deepcopy(ready)
            del record[field]
            self.assertFalse(self.check.is_valid(record))

    def test_cli_ready_invalid_json_missing_file_and_multiple_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            path.write_text(json.dumps(self.ready_record()))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--require-ready", str(path)]), 0)
                self.assertEqual(main(["--require-ready", str(path), str(ROOT / "example-review.json")]), 2)
                path.write_text("{invalid")
                self.assertEqual(main([str(path)]), 1)
                self.assertEqual(main([str(path.parent / "missing.json")]), 1)
                self.assertEqual(main(["--require-ready", str(ROOT / "example-review.json"), str(path)]), 1)


if __name__ == "__main__":
    unittest.main()
