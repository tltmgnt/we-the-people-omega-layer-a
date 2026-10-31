"""Integration checks for the synthetic intake-to-escalation pilot."""
import copy
import io
import json
from contextlib import redirect_stdout
import unittest

from scripts.validate_review import ROOT, main, validator


PILOT = ROOT / "pilots/benefits-process"


class BenefitsPilotTests(unittest.TestCase):
    def setUp(self):
        self.paths = [PILOT / "01-intake.json", PILOT / "02-escalated.json"]
        self.records = [json.loads(path.read_text()) for path in self.paths]

    def test_records_are_valid_and_remain_blocked(self):
        for record in self.records:
            with self.subTest(revision=record["revision"]):
                self.assertEqual(list(validator().iter_errors(record)), [])
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(list(map(str, self.paths))), 0)
            self.assertEqual(main(["--require-ready", *map(str, self.paths)]), 2)
        self.assertEqual(output.getvalue().count("VALID; BLOCKED"), 4)

    def test_revision_and_escalation_preserve_unresolved_issues(self):
        intake, outcome = self.records
        self.assertEqual(intake["review_status"], "DRAFT")
        self.assertEqual(outcome["review_status"], "LEGAL_REVIEW_REQUIRED")
        self.assertEqual(outcome["revision"], intake["revision"] + 1)
        for field in ["review_id", "proposal_id", "jurisdictions",
                      "unresolved_questions", "conditions", "jurisdictional_limitations"]:
            self.assertEqual(intake[field], outcome[field], field)
        self.assertTrue(outcome["unresolved_questions"])
        for record in self.records:
            self.assertNotIn("reviewer_id", record)
            self.assertNotIn("reviewed_at", record)
            self.assertEqual(record["legal_authorities"], [])

    def test_evidence_resolves_without_claiming_legal_authority(self):
        manifest = json.loads((PILOT / "sources.json").read_text())
        self.assertEqual(manifest["pilot_id"], self.records[0]["review_id"])
        self.assertEqual(manifest["legal_sources"], [])
        sources = {source["evidence_id"]: source for source in manifest["sources"]}
        self.assertEqual(len(sources), len(manifest["sources"]))
        for record in self.records:
            for evidence_id in record["evidence_ids"]:
                source = sources[evidence_id]
                path = PILOT / source["path"]
                self.assertTrue(path.is_file())
                headings = {
                    line[3:].strip().lower().replace(" ", "-")
                    for line in path.read_text().splitlines() if line.startswith("## ")
                }
                self.assertIn(source["anchor"], headings)
                self.assertTrue(source["kind"].startswith("synthetic_"))
                self.assertTrue(source["applicability"])
                self.assertRegex(source["source_date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_status_only_change_cannot_make_pilot_ready(self):
        for record in self.records:
            changed = copy.deepcopy(record)
            changed["review_status"] = "READY_FOR_HUMAN_DECISION"
            self.assertFalse(validator().is_valid(changed))


if __name__ == "__main__":
    unittest.main()
