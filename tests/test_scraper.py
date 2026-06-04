# -*- coding: utf-8 -*-
import unittest

from src.config import ScrapeConfig
from src.scraper import build_target_url


class TestScraper(unittest.TestCase):
    def test_build_target_url_page_one(self):
        config = ScrapeConfig()
        url = build_target_url(config, 1)
        self.assertTrue(url.startswith("https://shop.2motor.tw/collections/allmotor/"))
        self.assertIn("limit=50", url)
        self.assertNotIn("page=1", url)

    def test_build_target_url_with_page_and_keywords(self):
        config = ScrapeConfig(keywords="scooter")
        url = build_target_url(config, 3)
        self.assertIn("page=3", url)
        self.assertIn("limit=50", url)
        self.assertIn("q=scooter", url)


if __name__ == "__main__":
    unittest.main()
