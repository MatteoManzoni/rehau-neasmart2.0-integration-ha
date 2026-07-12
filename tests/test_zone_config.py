"""Tests for Rehau zone topology parsing."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "rehau_neasmart2"


def load_module(module_name: str, filename: str):
    """Load an integration module without importing Home Assistant."""
    spec = importlib.util.spec_from_file_location(module_name, PACKAGE_PATH / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

integration_package = types.ModuleType("custom_components.rehau_neasmart2")
integration_package.__path__ = [str(PACKAGE_PATH)]
sys.modules.setdefault("custom_components.rehau_neasmart2", integration_package)

load_module("custom_components.rehau_neasmart2.const", "const.py")
zone_config = load_module(
    "custom_components.rehau_neasmart2.zone_config",
    "zone_config.py",
)


class ZoneConfigTests(unittest.TestCase):
    """Exercise legacy and explicit topology formats."""

    def test_legacy_entries_span_all_five_bases(self):
        names = ",".join(f"Zone {index}" for index in range(1, 61))

        parsed = zone_config.parse_zone_entries(names)

        self.assertEqual((1, 1, "Zone 1"), parsed[0])
        self.assertEqual((2, 1, "Zone 13"), parsed[12])
        self.assertEqual((5, 12, "Zone 60"), parsed[-1])

    def test_explicit_entries_support_sparse_multi_base_layouts(self):
        parsed = zone_config.parse_zone_entries(
            "1.3:Kitchen, 3.8:Office, 5.12:Attic"
        )

        self.assertEqual(
            [(1, 3, "Kitchen"), (3, 8, "Office"), (5, 12, "Attic")],
            parsed,
        )

    def test_mixed_entries_keep_legacy_position_mapping(self):
        parsed = zone_config.parse_zone_entries("Kitchen,1.4:Office,Bedroom")

        self.assertEqual(
            [(1, 1, "Kitchen"), (1, 4, "Office"), (1, 3, "Bedroom")],
            parsed,
        )

    def test_duplicate_addresses_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate zone address 1.1"):
            zone_config.parse_zone_entries("Kitchen,1.1:Office")

    def test_empty_entries_are_rejected(self):
        for value in ("", "Kitchen,,Office", "1.2:"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                zone_config.parse_zone_entries(value)

    def test_invalid_addresses_are_rejected(self):
        for value in (
            "0.1:Kitchen",
            "6.1:Kitchen",
            "1.0:Kitchen",
            "1.13:Kitchen",
            "one.1:Kitchen",
            "1.2.3:Kitchen",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                zone_config.parse_zone_entries(value)

    def test_more_than_sixty_zones_are_rejected(self):
        names = ",".join(f"Zone {index}" for index in range(1, 62))

        with self.assertRaisesRegex(ValueError, "at most 60 zones"):
            zone_config.parse_zone_entries(names)


if __name__ == "__main__":
    unittest.main()
