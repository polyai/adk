"""Tests for shared region definitions and normalization.

Copyright PolyAI Limited
"""

import unittest

from poly.handlers.interface import REGIONS as INTERFACE_REGIONS
from poly.regions import ENTERPRISE_REGIONS, REGION_ALIASES, REGIONS, normalize_region


class RegionsTest(unittest.TestCase):
    def test_region_collections_use_canonical_identifiers(self):
        self.assertEqual(
            REGIONS,
            ["us-1", "euw-1", "uk-1", "studio", "staging", "dev"],
        )
        self.assertEqual(ENTERPRISE_REGIONS, ("us-1", "euw-1", "uk-1"))

    def test_interface_reexports_shared_regions(self):
        self.assertIs(INTERFACE_REGIONS, REGIONS)

    def test_normalize_region_preserves_canonical_regions(self):
        for region in REGIONS:
            with self.subTest(region=region):
                self.assertEqual(normalize_region(region), region)

    def test_normalize_region_expands_short_aliases(self):
        for alias, region in REGION_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertEqual(normalize_region(alias), region)

    def test_normalize_region_is_case_insensitive(self):
        self.assertEqual(normalize_region("US"), "us-1")
        self.assertEqual(normalize_region("EuW-1"), "euw-1")
        self.assertEqual(normalize_region("STUDIO"), "studio")

    def test_normalize_region_ignores_surrounding_whitespace(self):
        self.assertEqual(normalize_region("  UK  "), "uk-1")

    def test_normalize_region_rejects_unknown_region(self):
        with self.assertRaisesRegex(ValueError, "^Unknown region: mars-1$"):
            normalize_region("mars-1")


if __name__ == "__main__":
    unittest.main()
