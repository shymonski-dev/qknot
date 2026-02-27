import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from quantum_engine import validate_braid_problem_input


class BraidProblemValidationTests(unittest.TestCase):
    def test_accepts_contiguous_multi_generator_braid(self):
        analysis = validate_braid_problem_input("s1 s2^-1 s3 s2 s1^-1")

        self.assertEqual(analysis["token_count"], 5)
        self.assertEqual(analysis["generator_counts"], {"s1": 2, "s2": 2, "s3": 1})
        self.assertEqual(analysis["strand_count"], 4)
        self.assertEqual(analysis["required_qubits"], 5)
        self.assertTrue(analysis["is_contiguous_generator_range"])

    def test_rejects_braid_with_fewer_than_three_tokens(self):
        with self.assertRaisesRegex(ValueError, "at least three generators"):
            validate_braid_problem_input("s1 s2")

    def test_rejects_braid_with_only_one_distinct_generator(self):
        with self.assertRaisesRegex(ValueError, "at least two distinct generators"):
            validate_braid_problem_input("s1 s1 s1")

    def test_rejects_non_contiguous_generator_range(self):
        with self.assertRaisesRegex(ValueError, "Missing: s2"):
            validate_braid_problem_input("s1 s3 s1 s3")


if __name__ == "__main__":
    unittest.main()
