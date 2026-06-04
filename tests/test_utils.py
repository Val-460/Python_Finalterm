# -*- coding: utf-8 -*-
import unittest

from src.utils import safe_int, safe_float


class TestUtils(unittest.TestCase):
    def test_safe_int_with_integers(self):
        self.assertEqual(safe_int(123), 123)
        self.assertEqual(safe_int(0), 0)

    def test_safe_int_with_floats(self):
        self.assertEqual(safe_int(123.9), 123)
        self.assertEqual(safe_int(-12.5), -12)

    def test_safe_int_with_strings(self):
        self.assertEqual(safe_int("1,234"), 1234)
        self.assertEqual(safe_int("Price 567"), 567)
        self.assertIsNone(safe_int("abc"))

    def test_safe_float_with_numbers(self):
        self.assertAlmostEqual(safe_float(1.23), 1.23)
        self.assertAlmostEqual(safe_float(123), 123.0)

    def test_safe_float_with_strings(self):
        self.assertAlmostEqual(safe_float("1,234.56"), 1234.56)
        self.assertAlmostEqual(safe_float("Value 98.7"), 98.7)
        self.assertIsNone(safe_float("abc"))


if __name__ == "__main__":
    unittest.main()
