import unittest

from gate_common import matches, selected


class PathTests(unittest.TestCase):
    def test_root_and_nested_sources(self):
        for path in ("source.py", "src/source.ts", "deep/src/source.kt", "lib/main.cjs"):
            with self.subTest(path=path):
                self.assertTrue(selected(path))

    def test_builtin_and_user_excludes(self):
        for path in (
            "node_modules/a.js",
            "app/vendor/a.php",
            "dist/a.js",
            ".github-shared-ci/actions/a.py",
            "tests/source.py",
            "test_source.py",
            "src/test_source.py",
            "src/a.test.ts",
            "app/src/androidTest/a.kt",
        ):
            with self.subTest(path=path):
                self.assertFalse(selected(path))
        self.assertFalse(selected("generated/a.py", exclude="generated/**"))
        self.assertTrue(selected("tests/source.py", tests=False))

    def test_globs_respect_directory_boundaries(self):
        self.assertTrue(matches("a.py", "**/*.py"))
        self.assertTrue(matches("a/b/c.py", "**/*.py"))
        self.assertFalse(matches("src/deep/a.py", "src/*.py"))
