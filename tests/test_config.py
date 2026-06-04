# -*- coding: utf-8 -*-
import os
import unittest
from pathlib import Path

from src.config import output_paths


class TestConfig(unittest.TestCase):
    def test_output_paths_creates_outputs_dir(self):
        prefix = "testprefix"
        result = output_paths(prefix)
        self.assertIn("csv", result)
        self.assertIn("main_png", result)
        self.assertIn("excel", result)
        self.assertIn("html", result)
        self.assertTrue(result["csv"].endswith("_listings.csv"))
        self.assertTrue(result["main_png"].endswith("_analysis.png"))
        self.assertTrue(result["excel"].endswith("_report.xlsx"))
        self.assertTrue(result["html"].endswith("_report.html"))
        self.assertTrue(Path(result["csv"]).parent.exists())
        self.assertTrue(Path(result["main_png"]).parent.exists())
        self.assertTrue(Path(result["excel"]).parent.exists())
        self.assertTrue(Path(result["html"]).parent.exists())

    def test_output_paths_prefix_sanitization(self):
        result = output_paths("  myprefix  ")
        self.assertIn("myprefix_", Path(result["csv"]).name)
        self.assertIn("myprefix_", Path(result["main_png"]).name)


if __name__ == "__main__":
    unittest.main()
