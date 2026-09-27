"""Unit tests for coverage_gate.py — run with: python3 -m unittest discover -s actions/coverage-gate"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import coverage_gate

TESTDATA = Path(__file__).resolve().parent / "testdata"


def write_tmp(content: str) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8")
    with handle:
        handle.write(content)
    return handle.name


class ReadCoverageTest(unittest.TestCase):
    def test_clover_uses_project_level_metrics(self) -> None:
        result = coverage_gate.read_coverage(str(TESTDATA / "clover-85.xml"))
        self.assertEqual(result.format, "clover")
        self.assertEqual((result.covered, result.total), (34, 40))
        self.assertAlmostEqual(result.percent, 85.0)

    def test_cobertura_uses_line_counters(self) -> None:
        result = coverage_gate.read_coverage(str(TESTDATA / "cobertura-90.xml"))
        self.assertEqual(result.format, "cobertura")
        self.assertEqual((result.covered, result.total), (45, 50))
        self.assertAlmostEqual(result.percent, 90.0)

    def test_cobertura_falls_back_to_line_rate(self) -> None:
        path = write_tmp('<coverage line-rate="0.8125" branch-rate="0"><packages/></coverage>')
        self.addCleanup(os.unlink, path)
        result = coverage_gate.read_coverage(path)
        self.assertIsNone(result.total)
        self.assertAlmostEqual(result.percent, 81.25)

    def test_explicit_format_overrides_detection(self) -> None:
        with self.assertRaises(coverage_gate.CoverageError):
            coverage_gate.read_coverage(str(TESTDATA / "cobertura-90.xml"), "clover")

    def test_missing_file(self) -> None:
        with self.assertRaisesRegex(coverage_gate.CoverageError, "not found"):
            coverage_gate.read_coverage(str(TESTDATA / "nope.xml"))

    def test_invalid_xml(self) -> None:
        path = write_tmp("<coverage")
        self.addCleanup(os.unlink, path)
        with self.assertRaisesRegex(coverage_gate.CoverageError, "not valid XML"):
            coverage_gate.read_coverage(path)

    def test_unknown_root(self) -> None:
        path = write_tmp("<report/>")
        self.addCleanup(os.unlink, path)
        with self.assertRaisesRegex(coverage_gate.CoverageError, "unsupported root"):
            coverage_gate.read_coverage(path)

    def test_clover_without_statements_is_an_error(self) -> None:
        path = write_tmp('<coverage><project><metrics statements="0" coveredstatements="0"/></project></coverage>')
        self.addCleanup(os.unlink, path)
        with self.assertRaisesRegex(coverage_gate.CoverageError, "no executable"):
            coverage_gate.read_coverage(path)


class MainTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.output = Path(tmp.name) / "output"
        self.summary = Path(tmp.name) / "summary"
        self.env = {"GITHUB_OUTPUT": str(self.output), "GITHUB_STEP_SUMMARY": str(self.summary)}

    def run_main(self, *args: str) -> tuple[int, str]:
        buffer = io.StringIO()
        saved = {key: os.environ.get(key) for key in self.env}
        os.environ.update(self.env)
        try:
            with redirect_stdout(buffer):
                code = coverage_gate.main(list(args))
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        return code, buffer.getvalue()

    def test_passes_at_or_above_minimum(self) -> None:
        code, out = self.run_main(str(TESTDATA / "clover-85.xml"), "--min", "85")
        self.assertEqual(code, 0)
        self.assertIn("85.00% (34/40 lines) passed", out)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "percent=85.00\n")
        self.assertIn("✅", self.summary.read_text(encoding="utf-8"))

    def test_fails_below_minimum(self) -> None:
        code, out = self.run_main(str(TESTDATA / "clover-50.xml"), "--min", "80")
        self.assertEqual(code, 1)
        self.assertIn("::error title=Coverage gate::Line coverage 50.00%", out)
        self.assertIn("❌", self.summary.read_text(encoding="utf-8"))

    def test_fails_just_below_minimum(self) -> None:
        code, _ = self.run_main(str(TESTDATA / "cobertura-78.xml"), "--min", "78.5")
        self.assertEqual(code, 1)

    def test_error_exit_code_for_bad_report(self) -> None:
        code, out = self.run_main(str(TESTDATA / "nope.xml"))
        self.assertEqual(code, 2)
        self.assertIn("::error", out)


if __name__ == "__main__":
    unittest.main()
