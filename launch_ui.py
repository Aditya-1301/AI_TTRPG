#!/usr/bin/env python3
"""
TTRPG Session Manager UI Launcher
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.session_manager import main

if __name__ == "__main__":
    main()