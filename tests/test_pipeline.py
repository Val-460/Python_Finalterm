# -*- coding: utf-8 -*-
import queue
import unittest
from unittest.mock import patch

from src.config import ScrapeConfig
from src.pipeline import run_pipeline


class TestPipeline(unittest.TestCase):
    def test_run_pipeline_with_stubbed_scraper(self):
        config = ScrapeConfig(output_prefix="testpipeline")
        log_queue = queue.Queue()

        fake_data = [{
            "title": "車款A",
            "price": 100000,
            "url": "https://example.com/1",
            "mileage": 10000,
            "year": 2019,
            "cc": 125,
            "store": "店家A",
        }]

        with patch("src.pipeline.fetch_all_data", return_value=fake_data):
            result = run_pipeline(config, log_queue)

        self.assertEqual(result["rows"], 1)
        self.assertIn("DONE", [item[0] for item in list(log_queue.queue)])


if __name__ == "__main__":
    unittest.main()
