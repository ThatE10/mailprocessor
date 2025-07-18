"""
Test runner script for mail_reader package
"""
import unittest
import sys
import os

from mail_reader.tests.test_ad_detector import TestAdvertisementDetector
from mail_reader.tests.test_email_parser import TestEmailParser
from mail_reader.tests.test_email_processor import TestEmailProcessor
from mail_reader.tests.test_stats_manager import TestStatsManager

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import all test modules



def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestEmailParser),
        unittest.TestLoader().loadTestsFromTestCase(TestAdvertisementDetector),
        unittest.TestLoader().loadTestsFromTestCase(TestStatsManager),
        unittest.TestLoader().loadTestsFromTestCase(TestEmailProcessor)
    ])

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return 0 if tests passed, 1 if any failed
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
