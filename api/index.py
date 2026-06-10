# -*- coding: utf-8 -*-
import sys
import os

# Add the parent directory to Python path so we can import backend.server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.server import app
