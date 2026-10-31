import copy
import hashlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest

from scripts.validate_packet import ROOT, check_packet, load_json, main, read_pinned


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "examples/permit/operational-review.json"
        self.record = load_json(self.path.read_text())

    def test_example_is_valid_and_blocked(self):
        self.assertEqual(check_packet(self.record), (False, "LEGAL_REVIEW_REQUIRED"))
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main([str(self.path)]), 0)
            self.assertEqual(main(["--require-ready", str(self.path)]), 2)
        self.assertEqual(output.getvalue().count("VALID PACKET; BLOCKED"), 2)

    def test_all_required_fields_and_six_domains(self):
        for field in self.record:
            changed = copy.deepcopy(self.record)
            del changed[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_packet(changed)
        for domain in ["B1", "B2", "B3", "B4", "B5", "B6"]:
            changed = copy.deepcopy(self.record)
            del changed["domain_screening"][domain]
            with self.subTest(domain=domain), self.assertRaises(ValueError):
                check_packet(changed)

    def test_schema_rejects_wrong_types_versions_and_blank_values(self):
        for field, value in [
            ("revision", True), ("revision", 0), ("schema_version", "9.0.0"),
            ("review_status", "APPROVED"), ("proposal_id", "  "),
            ("unexpected", "field"), ("reviewed_at", "yesterday"),
        ]:
            changed = copy.deepcopy(self.record)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_packet(changed)

    def test_unknown_or_duplicate_evidence_and_identifiers(self):
        for mutate in [
            lambda r: r["evidence"].append(r["evidence"][0]),
            lambda r: r["metrics"].append(r["metrics"][0]),
            lambda r: r["gaps"].append(r["gaps"][0]),
            lambda r: r["metrics"][0].update(source_id="UNKNOWN"),
            lambda r: r["gaps"][0].update(evidence_ids=["UNKNOWN"]),
        ]:
            changed = copy.deepcopy(self.record)
            mutate(changed)
            with self.assertRaises(ValueError):
                check_packet(changed)

    def test_review_reference_identity_and_hashes(self):
        for field, value in [
            ("review_id", "OTHER"), ("revision", 99),
            ("schema_version", "9.0.0"), ("sha256", "0" * 64),
        ]:
            changed = copy.deepcopy(self.record)
            changed["layer_a_ref"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_packet(changed)
        changed = copy.deepcopy(self.record)
        changed["proposal_id"] = "OTHER"
        with self.assertRaises(ValueError):
            check_packet(changed)
        changed = copy.deepcopy(self.record)
        changed["evidence"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            check_packet(changed)

    def test_safe_reference_paths_and_symlinks(self):
        for path in ["/etc/passwd", "../outside"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                read_pinned({"path": path, "sha256": "0" * 64}, ROOT)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            root.mkdir()
            (base / "outside").write_text("{}")
            (root / "escape").symlink_to(base / "outside")
            with self.assertRaises(ValueError):
                read_pinned({"path": "escape", "sha256": "0" * 64}, root)

    def test_ready_cannot_override_layer_a_or_open_findings(self):
        changed = copy.deepcopy(self.record)
        changed.update(review_status="READY_FOR_HUMAN_DECISION",
                       reviewer_id="SYNTHETIC-REVIEWER",
                       reviewed_at="2026-10-31T12:00:00Z")
        with self.assertRaises(ValueError):
            check_packet(changed)
        changed.update(unresolved_questions=[], gaps=[])
        with self.assertRaisesRegex(ValueError, "Layer A hold"):
            check_packet(changed)

    def test_resolved_gap_requires_attribution_and_evidence(self):
        changed = copy.deepcopy(self.record)
        changed["gaps"][0]["status"] = "RESOLVED"
        with self.assertRaises(ValueError):
            check_packet(changed)
        changed["gaps"][0].update(
            verifier_id="SYNTHETIC-VERIFIER",
            verification_evidence_ids=["UNKNOWN"])
        with self.assertRaises(ValueError):
            check_packet(changed)
        changed["gaps"][0]["verification_evidence_ids"] = [
            self.record["evidence"][0]["evidence_id"]]
        self.assertFalse(check_packet(changed)[0])

    def copy_fixture(self, root, record):
        for reference in [record["layer_a_ref"], *record["evidence"]]:
            path = root / reference["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / reference["path"]).read_bytes())

    def test_consistent_synthetic_readiness_is_only_for_human_decision(self):
        changed = copy.deepcopy(self.record)
        changed.update(review_status="READY_FOR_HUMAN_DECISION",
                       reviewer_id="SYNTHETIC-REVIEWER",
                       reviewed_at="2026-10-31T12:00:00Z",
                       unresolved_questions=[], gaps=[])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_fixture(root, changed)
            ref = changed["layer_a_ref"]
            path = root / ref["path"]
            review = load_json(path.read_text())
            review.update(review_status="READY_FOR_HUMAN_DECISION",
                          reviewer_id="SYNTHETIC-LEGAL-REVIEWER",
                          reviewed_at="2026-10-31T12:00:00Z",
                          legal_authorities=["Synthetic test authority"],
                          conditions=[], jurisdictional_limitations=[],
                          unresolved_questions=[])
            path.write_text(json.dumps(review))
            ref["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(check_packet(changed, root),
                             (True, "READY_FOR_HUMAN_DECISION"))

    def test_pinned_invalid_layer_a_and_missing_evidence_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changed = copy.deepcopy(self.record)
            self.copy_fixture(root, changed)
            ref = changed["layer_a_ref"]
            path = root / ref["path"]
            review = load_json(path.read_text())
            for value in [
                {}, {**review, "evidence_ids": ["UNKNOWN"]},
                {**review, "reviewed_at": "invalid"},
            ]:
                path.write_text(json.dumps(value))
                ref["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.subTest(value=value), self.assertRaises(ValueError):
                    check_packet(changed, root)
            for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', bytes([255])]:
                path.write_bytes(raw)
                ref["sha256"] = hashlib.sha256(raw).hexdigest()
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    check_packet(changed, root)

    def test_strict_json_and_cli_failures(self):
        duplicate = '{"review_status":"DRAFT",' + json.dumps(self.record)[1:]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(path)]), 1)
                for value in [
                    duplicate, '{"nested":{"id":1,"id":2}}',
                    '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}',
                    "{broken", "[]", "null",
                ]:
                    path.write_text(value)
                    self.assertEqual(main([str(path)]), 1)

    def test_no_measured_results_are_invented(self):
        self.assertEqual(self.record["kind"], "SYNTHETIC")
        self.assertTrue(self.record["unresolved_questions"])
        for metric in self.record["metrics"]:
            self.assertIsNone(metric["value"])
            self.assertEqual(metric["sample_size"], 0)
            self.assertTrue(metric["counter_metric"])
            self.assertTrue(metric["uncertainty"])
        changed = copy.deepcopy(self.record)
        changed["metrics"][0]["value"] = 12
        with self.assertRaises(ValueError):
            check_packet(changed)

    def test_portfolio_slots_and_unresolved_entries_are_preserved(self):
        register = load_json((ROOT / "portfolio/project-register.json").read_text())
        self.assertEqual([p["project_id"] for p in register["projects"]],
                         [f"{i:03}" for i in range(1, 51)])
        self.assertEqual(len(register["unassigned_foundational_sources"]), 4)
        for project in register["projects"][:6]:
            self.assertIsNone(project["title"])
            self.assertIsNone(project["source_url"])
        self.assertEqual(register["projects"][6]["title"], "Civic Capacity Lab.")
        self.assertIsNone(register["projects"][6]["source_url"])
        self.assertEqual(set(register["layer_sources"]), {"A", "B", "C", "D", "E"})
        self.assertTrue(all(p["implementation_status"] == "PROPOSED_NOT_AUTHORIZED"
                            for p in register["projects"]))


if __name__ == "__main__":
    unittest.main()
