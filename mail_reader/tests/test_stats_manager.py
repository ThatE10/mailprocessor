"""
Unit tests for StatsManager
"""
import unittest
import json
import os
import tempfile
from ..utils.stats_manager import StatsManager

class TestStatsManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.temp_dir, 'test_stats.json')
        self.stats_manager = StatsManager(self.stats_file)

    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.stats_file):
            os.remove(self.stats_file)
        os.rmdir(self.temp_dir)

    def test_initial_stats(self):
        """Test initial statistics values"""
        stats = self.stats_manager.get_stats()
        self.assertEqual(stats['total_emails_processed'], 0)
        self.assertEqual(stats['total_advertisements'], 0)
        self.assertEqual(stats['unique_senders'], 0)
        self.assertEqual(stats['advertisement_rate'], 0)
        self.assertIsNone(stats['last_processed'])

    def test_update_stats(self):
        """Test updating statistics"""
        # Update with non-advertisement
        self.stats_manager.update_stats(False)
        stats = self.stats_manager.get_stats()
        self.assertEqual(stats['total_emails_processed'], 1)
        self.assertEqual(stats['total_advertisements'], 0)
        self.assertEqual(stats['advertisement_rate'], 0)

        # Update with advertisement
        self.stats_manager.update_stats(True)
        stats = self.stats_manager.get_stats()
        self.assertEqual(stats['total_emails_processed'], 2)
        self.assertEqual(stats['total_advertisements'], 1)
        self.assertEqual(stats['advertisement_rate'], 50.0)

    def test_save_and_load_stats(self):
        """Test saving and loading statistics"""
        # Update some stats
        self.stats_manager.update_stats(True)
        self.stats_manager.update_stats(False)
        self.stats_manager.update_stats(True)

        # Create new instance to test loading
        new_manager = StatsManager(self.stats_file)
        stats = new_manager.get_stats()
        self.assertEqual(stats['total_emails_processed'], 3)
        self.assertEqual(stats['total_advertisements'], 2)
        self.assertEqual(stats['advertisement_rate'], 66.67)

    def test_reset_stats(self):
        """Test resetting statistics"""
        # Update some stats
        self.stats_manager.update_stats(True)
        self.stats_manager.update_stats(False)

        # Reset stats
        self.stats_manager.reset_stats()
        stats = self.stats_manager.get_stats()
        self.assertEqual(stats['total_emails_processed'], 0)
        self.assertEqual(stats['total_advertisements'], 0)
        self.assertEqual(stats['advertisement_rate'], 0)
        self.assertIsNone(stats['last_processed']) 