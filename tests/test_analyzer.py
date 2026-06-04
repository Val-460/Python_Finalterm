# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest

from src.analyzer import analyze_and_plot
from src.config import ScrapeConfig


class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.outputs = {
            "csv": os.path.join(self.test_dir, "test_listings.csv"),
            "main_png": os.path.join(self.test_dir, "test_analysis.png"),
            "excel": os.path.join(self.test_dir, "test_report.xlsx"),
            "html": os.path.join(self.test_dir, "test_report.html"),
        }
        self.log_messages = []

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def log_callback(self, message: str):
        self.log_messages.append(message)

    def test_analyze_and_plot_creates_files(self):
        data_list = [
            {"title": "車款A", "price": "100000", "url": "https://example.com/1", "mileage": "10000", "year": "2019", "cc": "125", "store": "店家A"},
            {"title": "車款B", "price": "120000", "url": "https://example.com/2", "mileage": "8000", "year": "2020", "cc": "150", "store": "店家B"},
        ]

        df = analyze_and_plot(data_list, self.outputs, self.log_callback)

        self.assertEqual(len(df), 2)
        self.assertTrue(os.path.exists(self.outputs["csv"]))
        self.assertTrue(os.path.exists(self.outputs["main_png"]))
        self.assertTrue(os.path.exists(self.outputs["excel"]))
        self.assertTrue(os.path.exists(self.outputs["html"]))
        self.assertIn("已成功儲存 2 筆不重複的機車資料", "\n".join(self.log_messages))

    def test_analyze_and_plot_handles_empty_data(self):
        df = analyze_and_plot([], self.outputs, self.log_callback)
        self.assertTrue(df.empty)
        self.assertTrue(os.path.exists(self.outputs["csv"]))
        self.assertIn("已儲存空 CSV", "\n".join(self.log_messages))


if __name__ == "__main__":
    unittest.main()
