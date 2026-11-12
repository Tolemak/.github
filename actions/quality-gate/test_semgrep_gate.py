import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from semgrep_gate import evaluate, main


def finding(severity, rule="python.security.example"):
    return {
        "check_id": rule,
        "path": "source.py",
        "start": {"line": 3},
        "extra": {"severity": severity, "message": "Unsafe operation"},
    }


class SemgrepTests(unittest.TestCase):
    def test_blocking_severities_annotate(self):
        for severity in ("ERROR", "WARNING", "CRITICAL", "HIGH", "MEDIUM"):
            with self.subTest(severity=severity), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(evaluate({"results": [finding(severity)]}, 0), 1)
                self.assertIn("::error file=source.py,line=3::", output.getvalue())

    def test_info_and_low_are_reported(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(evaluate({"results": [finding("INFO"), finding("LOW")]}, 0), 0)
        self.assertEqual(output.getvalue().count("::notice"), 2)

    def test_excludes_short_id_only(self):
        with contextlib.redirect_stdout(io.StringIO()):
            report = {"results": [finding("ERROR")]}
            self.assertEqual(evaluate(report, 1, "example"), 0)
            self.assertEqual(evaluate(report, 1, "python.security.example"), 1)

    def test_scan_errors_fail_even_with_empty_results(self):
        for code in (2, 7, -1):
            with self.subTest(code=code), self.assertRaises(ValueError):
                evaluate({"results": []}, code)
        with self.assertRaises(ValueError):
            evaluate({"results": [], "errors": [{"message": "incomplete scan"}]}, 0)
        with self.assertRaises(ValueError):
            evaluate({"results": [], "errors": [{"level": "error", "message": "rule failed"}]}, 0)

    def test_partial_parsing_warnings_do_not_fail(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(evaluate({"results": [], "errors": [{"level": "warn", "message": "partial"}]}, 0), 0)
        self.assertIn("::warning::partial", output.getvalue())

    def test_missing_invalid_and_malformed_reports_fail(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory) / "report.json"
            self.assertEqual(main([str(path), "--exit-code", "0"]), 1)
            for content in ("", "not-json", "{}", '{"results":[{}]}'):
                path.write_text(content, encoding="utf-8")
                self.assertEqual(main([str(path), "--exit-code", "0"]), 1)

    def test_annotation_escapes_untrusted_values(self):
        item = finding("ERROR")
        item["path"] = "a,b:evil.py"
        item["extra"]["message"] = "first\n::notice::second%"
        with contextlib.redirect_stdout(io.StringIO()) as output:
            evaluate({"results": [item]}, 1)
        self.assertIn("a%2Cb%3Aevil.py", output.getvalue())
        self.assertIn("%0A::notice::second%25", output.getvalue())
