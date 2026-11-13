import contextlib
import fnmatch
import io
import unittest
from unittest.mock import patch

from coverage_scope import diff_command, evaluate, main, report_paths, source_patterns
from test_support import GitRepository


class CoverageTests(unittest.TestCase):
    def test_diff_include_treats_route_brackets_literally(self):
        path = "src/routes/[id].tsx"
        args = diff_command([], "base", 80, [path], [])
        self.assertTrue(fnmatch.fnmatchcase(path, args[args.index("--include") + 1]))

    def test_source_globs_accept_commas_and_spaces(self):
        self.assertEqual(
            source_patterns("src/**/*.py,lib/**/*.ts app/**/*.kt"), ("src/**/*.py", "lib/**/*.ts", "app/**/*.kt")
        )
        with self.assertRaises(ValueError):
            source_patterns("")

    def test_cobertura_sources_absolute_and_relative_paths(self):
        with GitRepository() as repo:
            source = repo.write("src/main.py", "value = 1\n")
            report = repo.write(
                "reports/coverage.xml",
                f"<coverage><sources><source>{repo.root.as_posix()}/src</source></sources>"
                f'<packages><class filename="main.py"/><class filename="{source.as_posix()}"/></packages></coverage>',
            )
            self.assertIn("src/main.py", report_paths(report, repo.root))

    def test_clover_lcov_and_jacoco_paths(self):
        with GitRepository() as repo:
            clover = repo.write(
                "clover.xml", f'<coverage><project><file name="{repo.root.as_posix()}/src/a.php"/></project></coverage>'
            )
            lcov = repo.write("lcov.info", f"SF:{repo.root.as_posix()}/src/a.js\nDA:1,1\nend_of_record\n")
            jacoco = repo.write(
                "jacoco.xml", '<report><package name="com/example"><sourcefile name="App.kt"/></package></report>'
            )
            self.assertIn("src/a.php", report_paths(clover, repo.root))
            self.assertIn("src/a.js", report_paths(lcov, repo.root))
            self.assertIn("src/main/kotlin/com/example/App.kt", report_paths(jacoco, repo.root, ["src/main/kotlin"]))

    def test_no_changed_source_files_pass_without_reports(self):
        with GitRepository() as repo:
            base = repo.commit()
            repo.write("README.md", "Updated\n")
            repo.write("tests/test_source.py", "value = 1\n")
            repo.commit()
            self.assertEqual(evaluate(repo.root, base, repo.root / "missing", 80), 0)

    def test_missing_reports_and_missing_source_fail_before_diff_cover(self):
        with GitRepository() as repo, contextlib.redirect_stdout(io.StringIO()):
            base = repo.commit()
            repo.write("src/main.py", "value = 1\n")
            repo.commit()
            reports = repo.root / "reports"
            with patch("coverage_scope.subprocess.call") as run:
                self.assertEqual(evaluate(repo.root, base, reports, 80), 1)
                repo.write(
                    "reports/coverage.xml", '<coverage><packages><class filename="other.py"/></packages></coverage>'
                )
                self.assertEqual(evaluate(repo.root, base, reports, 80), 1)
                run.assert_not_called()

    def test_combines_reports_and_propagates_diff_failure(self):
        with GitRepository() as repo:
            base = repo.commit()
            repo.write("src/a.py", "value = 1\n")
            repo.write("src/b.js", "const value = 1;\n")
            repo.commit()
            repo.write("reports/a.xml", '<coverage><packages><class filename="src/a.py"/></packages></coverage>')
            repo.write("reports/nested/b.info", "SF:src/b.js\nDA:1,0\nend_of_record\n")
            with patch("coverage_scope.subprocess.call", side_effect=[0, 1]) as run:
                self.assertEqual(evaluate(repo.root, base, repo.root / "reports", 80), 1)
                xml_args, lcov_args = (call.args[0] for call in run.call_args_list)
                self.assertIn(f"--compare-branch={base}", xml_args)
                self.assertIn("--diff-range-notation=..", xml_args)
                self.assertIn("src/a.py", xml_args)
                self.assertNotIn("src/b.js", xml_args)
                self.assertTrue(any(arg.endswith("b.info") for arg in lcov_args))
                self.assertIn("src/b.js", lcov_args)
                self.assertNotIn("src/a.py", lcov_args)
            with patch("coverage_scope.subprocess.call", return_value=0):
                self.assertEqual(evaluate(repo.root, base, repo.root / "reports", 80), 0)

    def test_exclusions_and_custom_coverage_paths(self):
        with GitRepository() as repo:
            base = repo.commit()
            repo.write("src/a.py", "value = 1\n")
            repo.write("generated/a.py", "value = 2\n")
            repo.commit()
            self.assertEqual(evaluate(repo.root, base, repo.root / "missing", 80, ("src/*.ts",)), 0)
            self.assertEqual(evaluate(repo.root, base, repo.root / "missing", 80, exclude="src/**,generated/**"), 0)

    def test_declarations_and_tool_configs_need_no_coverage(self):
        with GitRepository() as repo:
            base = repo.commit()
            repo.write("src/global.d.ts", "declare const value: number;\n")
            repo.write("vitest.config.ts", "export default {};\n")
            repo.write("packages/config/eslint.config.js", "export default [];\n")
            repo.commit()
            self.assertEqual(evaluate(repo.root, base, repo.root / "missing", 80), 0)

    def test_scope_only_validates_without_running_diff_cover(self):
        with GitRepository() as repo:
            base = repo.commit()
            repo.write("src/main.py", "value = 1\n")
            repo.commit()
            repo.write(
                "reports/coverage.xml", '<coverage><packages><class filename="src/main.py"/></packages></coverage>'
            )
            with patch("coverage_scope.subprocess.call") as run:
                self.assertEqual(evaluate(repo.root, base, repo.root / "reports", 80, scope_only=True), 0)
                run.assert_not_called()

    def test_renamed_source_requires_report_under_new_name(self):
        with GitRepository() as repo, contextlib.redirect_stdout(io.StringIO()):
            repo.write("old.py", "value = 1\n")
            base = repo.commit()
            repo.git("mv", "old.py", "new.py")
            repo.commit()
            repo.write("reports/coverage.xml", '<coverage><packages><class filename="old.py"/></packages></coverage>')
            self.assertEqual(evaluate(repo.root, base, repo.root / "reports", 80), 1)

    def test_malformed_reports_fail(self):
        with GitRepository() as repo, contextlib.redirect_stdout(io.StringIO()):
            base = repo.commit()
            repo.write("source.py", "value = 1\n")
            repo.commit()
            repo.write("reports/coverage.xml", "broken")
            self.assertEqual(
                main(["--path", str(repo.root), "--base", base, "--coverage-dir", str(repo.root / "reports")]), 1
            )

    def test_partially_missing_sources_warn_and_measured_ones_are_checked(self):
        with GitRepository() as repo:
            base = repo.commit()
            repo.write("src/a.py", "value = 1\n")
            repo.write("src/port.py", "class Port: ...\n")
            repo.commit()
            repo.write("reports/a.xml", '<coverage><packages><class filename="src/a.py"/></packages></coverage>')
            with (
                patch("coverage_scope.subprocess.call", return_value=0) as run,
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(evaluate(repo.root, base, repo.root / "reports", 80), 0)
            self.assertIn("::warning::src/port.py", output.getvalue())
            self.assertIn("src/a.py", run.call_args.args[0])
            self.assertNotIn("src/port.py", run.call_args.args[0])
