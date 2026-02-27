import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from quantum_engine import compile_dowker_notation


class KnotIngestionCompilerTests(unittest.TestCase):
    def test_returns_catalog_mapping_for_known_trefoil_notation(self):
        result = compile_dowker_notation("4 6 2")

        self.assertEqual(result["dowker_notation_normalized"], "4 6 2")
        self.assertEqual(result["crossing_count"], 3)
        self.assertEqual(result["knot_name"], "Trefoil Knot (3_1)")
        self.assertEqual(result["braid_word"], "s1 s2^-1 s1 s2^-1")
        self.assertEqual(result["root_of_unity"], 5)
        self.assertTrue(result["is_catalog_match"])

    def test_accepts_commas_and_negative_values(self):
        result = compile_dowker_notation("4,-6,2")

        self.assertEqual(result["dowker_notation_normalized"], "4 -6 2")
        self.assertEqual(result["crossing_count"], 3)
        self.assertEqual(result["knot_name"], "Trefoil Knot (3_1)")
        self.assertTrue(result["is_catalog_match"])

    def test_builds_fallback_mapping_for_valid_non_catalog_notation(self):
        result = compile_dowker_notation("2 4 6 8 10 12")

        self.assertEqual(result["dowker_notation_normalized"], "2 4 6 8 10 12")
        self.assertEqual(result["crossing_count"], 6)
        self.assertEqual(result["knot_name"], "Dowker Knot (6 crossings)")
        self.assertEqual(result["root_of_unity"], 5)
        self.assertFalse(result["is_catalog_match"])
        self.assertEqual(
            result["braid_word"],
            "s1 s2 s1 s2 s1 s2",
        )

    def test_rejects_odd_value(self):
        with self.assertRaisesRegex(ValueError, "must be even"):
            compile_dowker_notation("4 3 2")

    def test_rejects_non_sequential_absolute_values(self):
        with self.assertRaisesRegex(ValueError, "complete even sequence"):
            compile_dowker_notation("4 10 2")


if __name__ == "__main__":
    unittest.main()
