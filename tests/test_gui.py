# -*- coding: utf-8 -*-
import tkinter as tk
import unittest

from src.gui import App


class TestGui(unittest.TestCase):
    def test_gui_can_initialize(self):
        root = tk.Tk()
        root.withdraw()
        app = App(root)
        self.assertIsNotNone(app)
        self.assertFalse(app.running)
        root.destroy()


if __name__ == "__main__":
    unittest.main()
