"""test_runner.py
Simple unittest discovery helper so other modules (e.g. root.py) can
execute the full test-suite programmatically.

Usage:
    from test_runner import run_tests
    success = run_tests()  # returns bool
"""

import unittest
from pathlib import Path
import sys


def run_tests(verbosity: int = 2) -> bool:
    """Discover and run all unittests in ./tests. Return True if green."""
    root = Path(__file__).parent
    # Ensure project root on sys.path for absolute imports
    sys.path.insert(0, str(root))
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return result.wasSuccessful()
