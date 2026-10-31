import copy
import hashlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest

from scripts.validate_exchange import ExchangeError, ROOT, check_exchange, main, read_pinned


class CrossLayerExchangeTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "examples/cross-layer/exchange.json"
        self.exchange = json.loads(self.path.read_text())

    def test_valid_exchange_reports_blocked(self):
        self.assertEqual(check_exchange(self.exchange), "LEGAL_REVIEW_REQUIRED")
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main([str(self.path)]), 0)
            self.assertEqual(main(["--require-ready", str(self.path)]), 2)
        self.assertEqual(output.getvalue().count("VALID EXCHANGE; BLOCKED"), 2)

    def test_mismatched_proposal_and_review_identity(self):
        for layer, field, value in [
            ("layer_c", "proposal_id", "OTHER"), ("layer_d", "proposal_id", "OTHER"),
            ("layer_a_ref", "proposal_id", "OTHER"), ("layer_a_ref", "review_id", "OTHER"),
            ("layer_a_ref", "revision", 99),
        ]:
            with self.subTest(layer=layer, field=field):
                changed = copy.deepcopy(self.exchange)
                changed[layer][field] = value
                with self.assertRaises(ExchangeError):
                    check_exchange(changed)

    def test_unknown_versions_and_fields_are_rejected(self):
        for layer in [None, "layer_b", "layer_c", "layer_a_ref", "layer_d"]:
            changed = copy.deepcopy(self.exchange)
            target = changed if layer is None else changed[layer]
            target["schema_version"] = "9.0.0"
            with self.subTest(layer=layer), self.assertRaises(ExchangeError):
                check_exchange(changed)
        changed = copy.deepcopy(self.exchange)
        changed["approved"] = True
        with self.assertRaises(ExchangeError):
            check_exchange(changed)

    def test_stale_record_and_manifest_hashes_are_rejected(self):
        for reference in ["layer_a_ref", "manifest_ref"]:
            changed = copy.deepcopy(self.exchange)
            target = changed["layer_a_ref"] if reference == "layer_a_ref" else changed["layer_d"]["manifest_ref"]
            target["sha256"] = "0" * 64
            with self.subTest(reference=reference), self.assertRaises(ExchangeError):
                check_exchange(changed)

    def test_evidence_must_resolve_and_cover_review(self):
        for identifiers in [["UNKNOWN"], ["PILOT-PROPOSAL-001"]]:
            changed = copy.deepcopy(self.exchange)
            changed["layer_d"]["evidence_ids"] = identifiers
            with self.subTest(identifiers=identifiers), self.assertRaises(ExchangeError):
                check_exchange(changed)

    def test_reference_paths_cannot_escape_root(self):
        for path in ["/etc/passwd", "../outside.json"]:
            with self.subTest(path=path), self.assertRaises(ExchangeError):
                read_pinned({"path": path, "sha256": "0" * 64}, ROOT)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            root.mkdir()
            (base / "outside.json").write_text("{}")
            (root / "escape.json").symlink_to(base / "outside.json")
            with self.assertRaises(ExchangeError):
                read_pinned({"path": "escape.json", "sha256": "0" * 64}, root)

    def test_cli_bad_json_missing_input_and_nonobject(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "exchange.json"
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(path)]), 1)
                for value in ["{bad", "[]", "null"]:
                    path.write_text(value)
                    self.assertEqual(main([str(path)]), 1)

    def test_invalid_pinned_review_and_manifest_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changed = copy.deepcopy(self.exchange)
            for reference in [changed["layer_a_ref"], changed["layer_d"]["manifest_ref"]]:
                path = root / reference["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / reference["path"]).read_bytes())
            manifest_ref = changed["layer_d"]["manifest_ref"]
            manifest_path = root / manifest_ref["path"]
            original = json.loads(manifest_path.read_text())
            wrong_pilot = copy.deepcopy(original)
            wrong_pilot["pilot_id"] = "OTHER"
            duplicate = copy.deepcopy(original)
            duplicate["sources"].append(duplicate["sources"][0])
            for value in [[], wrong_pilot, duplicate, {"pilot_id": "PILOT-A-BENEFITS-001", "sources": [None]}]:
                manifest_path.write_text(json.dumps(value))
                manifest_ref["sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                with self.subTest(value=value), self.assertRaises(ExchangeError):
                    check_exchange(changed, root=root)
            manifest_path.write_text(json.dumps(original))
            manifest_ref["sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            reference = changed["layer_a_ref"]
            path = root / reference["path"]
            path.write_text("{}")
            reference["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(ExchangeError):
                check_exchange(changed, root=root)


if __name__ == "__main__":
    unittest.main()
