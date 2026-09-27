import io
import unittest
from contextlib import redirect_stdout

from slugify import main, slugify


class SlugifyTest(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_diacritics(self) -> None:
        self.assertEqual(slugify("Zażółć gęślą jaźń"), "zazoc-gesla-jazn")

    def test_separator(self) -> None:
        self.assertEqual(slugify("a b", "_"), "a_b")

    def test_empty_separator(self) -> None:
        with self.assertRaises(ValueError):
            slugify("a", "")

    def test_main(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["A B", "C"]), 0)
        self.assertEqual(out.getvalue(), "a-b\nc\n")
