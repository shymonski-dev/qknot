import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from quantum_engine import parse_braid_word


class ParseBraidWordTests(unittest.TestCase):
    def test_parses_expanded_supported_tokens(self):
        self.assertEqual(
            parse_braid_word("s1 s2^-1 s12^-1 s3"),
            [(1, False), (2, True), (12, True), (3, False)],
        )

    def test_rejects_zero_generator_token(self):
        with self.assertRaisesRegex(ValueError, "Unsupported braid token"):
            parse_braid_word("s0")

    def test_rejects_non_braid_token(self):
        with self.assertRaisesRegex(ValueError, "Unsupported braid token"):
            parse_braid_word("x3")

    def test_rejects_blank_braid_word(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            parse_braid_word("   ")


if __name__ == "__main__":
    unittest.main()
