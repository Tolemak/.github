import contextlib
import io
import unittest

from complexity_gate import evaluate, regressions
from test_support import GitRepository


def function(branches, name="calculate"):
    body = "".join(f"    if value == {index}:\n        return {index}\n" for index in range(branches))
    return f"def {name}(value):\n{body}    return -1\n"


class ComplexityTests(unittest.TestCase):
    def test_existing_complexity_passes_until_it_grows(self):
        old = function(5)
        self.assertEqual(list(regressions("source.py", old, old + "\n", 3)), [])
        self.assertEqual(list(regressions("source.py", old, function(4), 3)), [])
        self.assertEqual(len(list(regressions("source.py", old, function(6), 3))), 1)

    def test_signature_annotations_keep_function_identity(self):
        old = function(5)
        annotated = old.replace("def calculate(value):", "def calculate(value: int) -> int:")
        self.assertEqual(list(regressions("source.py", old, annotated, 3)), [])

    def test_new_function_and_threshold_boundary(self):
        self.assertEqual(list(regressions("source.py", "", function(2), 3)), [])
        self.assertEqual(len(list(regressions("source.py", "", function(3), 3))), 1)

    def test_duplicate_names_follow_occurrence_order(self):
        old = function(5) + "\n" + function(3)
        new = function(5) + "\n" + function(4)
        failures = list(regressions("source.py", old, new, 3))
        self.assertEqual(len(failures), 1)
        self.assertGreater(failures[0].start_line, 1)

    def test_languages(self):
        snippets = {
            "py": function(3),
            "ts": "function calculate(v: number) { if(v) { if(v > 1) { return 1; } } return 0; }",
            "js": "function calculate(v) { if(v) { if(v > 1) { return 1; } } return 0; }",
            "php": "<?php function calculate($v) { if($v) { if($v > 1) { return 1; } } return 0; }",
            "kt": "fun calculate(v: Int): Int { if(v > 0) { if(v > 1) { return 1 } }; return 0 }",
        }
        for extension, source in snippets.items():
            with self.subTest(extension=extension):
                self.assertTrue(list(regressions(f"source.{extension}", "", source, 2)))

    def test_renames_and_deleted_files(self):
        with GitRepository() as repo, contextlib.redirect_stdout(io.StringIO()):
            repo.write("old.py", function(8))
            repo.write("deleted.py", function(9))
            base = repo.commit()
            repo.git("mv", "old.py", "new.py")
            repo.git("rm", "deleted.py")
            repo.commit()
            self.assertEqual(evaluate(repo.root, base, 3), 0)
            repo.write("new.py", function(10))
            repo.commit()
            self.assertEqual(evaluate(repo.root, base, 3), 1)

    def test_added_modified_and_excluded_files(self):
        with GitRepository() as repo, contextlib.redirect_stdout(io.StringIO()):
            repo.write("src/old.py", function(1))
            base = repo.commit()
            repo.write("src/old.py", function(4))
            repo.write("src/new.py", function(4))
            repo.write("tests/sample.py", function(4))
            repo.write("vendor/sample.py", function(4))
            repo.write("unrelated.go", "package main")
            repo.commit()
            self.assertEqual(evaluate(repo.root, base, 3), 1)
            self.assertEqual(evaluate(repo.root, base, 3, "src/**"), 0)
