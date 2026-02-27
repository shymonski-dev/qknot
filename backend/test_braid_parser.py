import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from quantum_engine import parse_braid_word


class ParseBraidWordTests(unittest.TestCase):
    def test_parses_supported_tokens(self):
        self.assertEqual(
            parse_braid_word("s1 s2^-1 s1^-1 s2"),
            [(1, False), (2, True), (1, True), (2, False)],
        )

    def test_rejects_unsupported_token(self):
        with self.assertRaisesRegex(ValueError, "Unsupported braid token"):
            parse_braid_word("s3")

    def test_rejects_blank_braid_word(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            parse_braid_word("   ")


if __name__ == "__main__":
    unittest.main()
