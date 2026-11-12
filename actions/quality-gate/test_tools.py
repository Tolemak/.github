import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import complexity_gate
import coverage_scope
import duplication_gate
import prepare_rules
import verdict


class ToolTests(unittest.TestCase):
    def test_duplication_threshold_and_new_clone_commands(self):
        with patch("duplication_gate.subprocess.call", return_value=1) as run:
            self.assertEqual(duplication_gate.main(["--max", "3"]), 1)
            self.assertIn("--threshold", run.call_args.args[0])
            self.assertIn("3.0", run.call_args.args[0])
            self.assertEqual(duplication_gate.main(["--base", "abc123"]), 1)
            self.assertIn("--baseline-from-ref", run.call_args.args[0])
            self.assertIn("--fail-on-new-clones", run.call_args.args[0])
            self.assertNotIn("--threshold", run.call_args.args[0])

    def test_duplication_rejects_invalid_threshold_and_missing_tool(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(duplication_gate.main(["--max", "-1"]), 1)
            with patch("duplication_gate.subprocess.call", side_effect=OSError("missing")):
                self.assertEqual(duplication_gate.main([]), 1)

    def test_prepare_copies_only_manifest_and_replaces_stale_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "rule.yaml").write_text("rules: []\n", encoding="utf-8")
            (source / "unlisted.yaml").write_text("not copied\n", encoding="utf-8")
            manifest = root / "manifest.txt"
            manifest.write_text("rule.yaml\n", encoding="utf-8")
            target = root / "rules"
            target.mkdir()
            (target / "stale.yaml").touch()
            prepare_rules.prepare(source, target, manifest)
            self.assertEqual([path.name for path in target.iterdir()], ["rule.yaml"])
            self.assertEqual((target / "rule.yaml").read_text(encoding="utf-8"), "rules: []\n")
            manifest.write_text("../escape.yaml\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare_rules.prepare(source, target, manifest)

    def test_verdict_fails_missing_or_failed_checks_and_records_table(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / "summary.md"
            env = dict.fromkeys(verdict.CHECKS.values(), "success")
            env.update(GITHUB_STEP_SUMMARY=str(summary), BASE="base")
            with patch.dict(os.environ, env):
                self.assertEqual(verdict.main(), 0)
                os.environ["SEMGREP"] = "failure"
                self.assertEqual(verdict.main(), 1)
                os.environ["SEMGREP"] = ""
                self.assertEqual(verdict.main(), 1)
            content = summary.read_text(encoding="utf-8")
            self.assertIn("| Check | Result | Detail |", content)
            self.assertIn("| semgrep | failure |", content)

    def test_verdict_allows_skipped_checks_without_base(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as output:
            env = dict.fromkeys(verdict.CHECKS.values(), "skipped")
            env.update(GITHUB_STEP_SUMMARY=str(Path(directory) / "summary.md"), BASE="")
            with patch.dict(os.environ, env):
                self.assertEqual(verdict.main(), 0)
            self.assertIn("::notice::", output.getvalue())

    def test_disabled_complexity_and_coverage_skip_without_git(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(complexity_gate.main(["--base", "", "--max", "0"]), 0)
            self.assertEqual(coverage_scope.main(["--base", "", "--coverage-dir", "absent"]), 0)
            self.assertEqual(complexity_gate.main(["--base", "bad", "--max", "-1"]), 1)
            self.assertEqual(coverage_scope.main(["--base", "bad", "--coverage-dir", "absent", "--min", "101"]), 1)

    def test_complexity_cli_propagates_result_and_errors(self):
        with patch("complexity_gate.evaluate", return_value=1) as evaluate:
            self.assertEqual(complexity_gate.main(["--base", "abc123"]), 1)
            self.assertEqual(evaluate.call_args.args[1:3], ("abc123", 15))
        with (
            patch("complexity_gate.evaluate", side_effect=OSError("missing")),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(complexity_gate.main(["--base", "abc123"]), 1)
