import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from quantum_engine import (
    compile_dowker_notation,
    _parse_knotinfo_braid_notation,
    _parse_knotinfo_dt_key,
    _load_knotinfo_catalog,
)


class KnotIngestionCompilerTests(unittest.TestCase):
    def test_returns_catalog_mapping_for_known_trefoil_notation(self):
        result = compile_dowker_notation("4 6 2")

        self.assertEqual(result["dowker_notation_normalized"], "4 6 2")
        self.assertEqual(result["crossing_count"], 3)
        self.assertEqual(result["knot_name"], "Trefoil Knot (3_1)")
        self.assertEqual(result["braid_word"], "s1 s2 s1 s2")
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
            "s1 s2 s3 s4 s1 s2",
        )

    def test_rejects_odd_value(self):
        with self.assertRaisesRegex(ValueError, "must be even"):
            compile_dowker_notation("4 3 2")

    def test_rejects_non_sequential_absolute_values(self):
        with self.assertRaisesRegex(ValueError, "complete even sequence"):
            compile_dowker_notation("4 10 2")


class KnotInfoCatalogTests(unittest.TestCase):
    def test_database_knotinfo_importable(self):
        """Phase 9a gate: database_knotinfo must be installed."""
        try:
            from database_knotinfo import link_list  # noqa: F401
        except ModuleNotFoundError:
            self.fail("database_knotinfo is not installed — KnotInfo catalog unavailable")

    def test_braid_notation_parser_simple(self):
        result = _parse_knotinfo_braid_notation("{1,-2,1,-2}")
        self.assertEqual(result, "s1 s2^-1 s1 s2^-1")

    def test_braid_notation_parser_br_wrapper(self):
        result = _parse_knotinfo_braid_notation("BR(3, {1,-2,1,-2})")
        self.assertEqual(result, "s1 s2^-1 s1 s2^-1")

    def test_braid_notation_parser_all_positive(self):
        result = _parse_knotinfo_braid_notation("{1,1,1}")
        self.assertEqual(result, "s1 s1 s1")

    def test_dt_key_parser_bracket_format(self):
        result = _parse_knotinfo_dt_key("[4, 6, 2]")
        self.assertEqual(result, (4, 6, 2))

    def test_dt_key_parser_handles_negative_values(self):
        # KnotInfo stores negative DT values for some knots (e.g. 8_19)
        result = _parse_knotinfo_dt_key("[4, 8, -12, 2, -14, -16, -6, -10]")
        self.assertEqual(result, (4, 8, 12, 2, 14, 16, 6, 10))

    def test_catalog_loads_and_has_many_entries(self):
        catalog = _load_knotinfo_catalog()
        self.assertGreater(len(catalog), 100)

    def test_six_crossing_knot_resolves_via_knotinfo(self):
        # 6_1 has DT notation [4, 8, 12, 10, 2, 6] in KnotInfo
        result = compile_dowker_notation("4 8 12 10 2 6")
        self.assertTrue(result["is_catalog_match"])
        self.assertEqual(result["knot_name"], "6_1")
        self.assertIsNotNone(result["braid_index"])
        # Braid word must parse without error
        from quantum_engine import parse_braid_word
        tokens = parse_braid_word(result["braid_word"])
        self.assertGreater(len(tokens), 0)

    def test_ten_crossing_knot_resolves_via_knotinfo(self):
        # 10_1 has DT notation [4, 12, 20, 18, 16, 14, 2, 10, 8, 6] in KnotInfo
        result = compile_dowker_notation("4 12 20 18 16 14 2 10 8 6")
        self.assertTrue(result["is_catalog_match"])
        self.assertEqual(result["knot_name"], "10_1")
        self.assertEqual(result["braid_index"], 6)


class HomflyPtTests(unittest.TestCase):
    def test_tier1_trefoil_has_homfly_pt(self):
        result = compile_dowker_notation("4 6 2")
        self.assertIsNotNone(result["homfly_pt"])
        self.assertIn("v", result["homfly_pt"])
        self.assertIn("z", result["homfly_pt"])

    def test_tier1_figure_eight_has_homfly_pt(self):
        result = compile_dowker_notation("4 6 8 2")
        self.assertIsNotNone(result["homfly_pt"])
        self.assertEqual(result["homfly_pt"], "(v^(-2)-1+v^2)+(-1)*z^2")

    def test_tier2_knotinfo_knot_has_homfly_pt(self):
        # 6_1 is in KnotInfo tier-2; it should have a HOMFLY-PT polynomial
        result = compile_dowker_notation("4 8 12 10 2 6")
        self.assertTrue(result["is_catalog_match"])
        self.assertIsNotNone(result["homfly_pt"])

    def test_tier3_fallback_has_no_homfly_pt(self):
        result = compile_dowker_notation("2 4 6 8 10 12")
        self.assertFalse(result["is_catalog_match"])
        self.assertIsNone(result["homfly_pt"])

    def test_homfly_pt_field_always_present(self):
        # All three tiers must return homfly_pt key (value may be None)
        for notation in ("4 6 2", "4 8 12 10 2 6", "2 4 6 8 10 12"):
            result = compile_dowker_notation(notation)
            self.assertIn("homfly_pt", result, f"homfly_pt key missing for notation: {notation}")


if __name__ == "__main__":
    unittest.main()
