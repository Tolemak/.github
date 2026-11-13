import contextlib
import io
import unittest

from needs_gate import evaluate, main


class NeedsTests(unittest.TestCase):
    def test_success_and_empty_needs_pass(self):
        self.assertEqual(evaluate({}), 0)
        self.assertEqual(evaluate({"unit": {"result": "success"}}), 0)

    def test_failed_cancelled_and_skipped_fail(self):
        with contextlib.redirect_stdout(io.StringIO()):
            for result in ("failure", "cancelled", "skipped", "unknown", None):
                with self.subTest(result=result):
                    self.assertEqual(evaluate({"unit": {"result": result}}), 1)

    def test_allowlist_only_allows_exact_skipped_job(self):
        self.assertEqual(evaluate({"optional": {"result": "skipped"}}, "other optional"), 0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluate({"optional": {"result": "failure"}}, "optional"), 1)
            self.assertEqual(evaluate({"optional": {"result": "skipped"}}, "optional-extra"), 1)

    def test_invalid_json_and_result_shapes_fail(self):
        with contextlib.redirect_stdout(io.StringIO()):
            for value in ("[1]", "null", "bad", '{"unit":null}', '{"unit":{}}'):
                with self.subTest(value=value):
                    self.assertEqual(main(["--needs", value]), 1)
