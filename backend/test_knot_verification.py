import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from quantum_engine import verify_topological_mapping


class KnotVerificationTests(unittest.TestCase):
    def test_verifies_connected_three_strand_braid(self):
        result = verify_topological_mapping("s1 s2^-1 s1 s2^-1")

        self.assertTrue(result["is_verified"])
        self.assertEqual(result["status"], "verified")
        self.assertIn("passed", result["detail"].lower())
        self.assertEqual(result["evidence"]["token_count"], 4)
        self.assertEqual(result["evidence"]["generator_counts"], {"s1": 2, "s2": 2})
        self.assertEqual(result["evidence"]["inverse_count"], 2)
        self.assertEqual(result["evidence"]["net_writhe"], 0)

    def test_fails_when_too_few_generators(self):
        result = verify_topological_mapping("s1 s2")

        self.assertFalse(result["is_verified"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("at least three generators", result["detail"].lower())

    def test_fails_when_braid_uses_only_single_generator(self):
        result = verify_topological_mapping("s1 s1 s1")

        self.assertFalse(result["is_verified"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("include both s1 and s2", result["detail"])
        self.assertEqual(result["evidence"]["strand_connectivity"], "partial-3-strand")

    def test_raises_for_invalid_token(self):
        with self.assertRaisesRegex(ValueError, "Unsupported braid token"):
            verify_topological_mapping("s1 s3")


if __name__ == "__main__":
    unittest.main()
