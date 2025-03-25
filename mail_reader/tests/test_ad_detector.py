"""
Unit tests for AdvertisementDetector
"""
import unittest
from ..utils.ad_detector import AdvertisementDetector

class TestAdvertisementDetector(unittest.TestCase):
    def setUp(self):
        self.detector = AdvertisementDetector()

    def test_is_advertisement(self):
        # Test with clear advertisement
        text = "Special offer! Limited time discount on our products. Buy now!"
        self.assertTrue(self.detector.is_advertisement(text))

        # Test with no advertisement indicators
        text = "Hello, how are you? Just checking in."
        self.assertFalse(self.detector.is_advertisement(text))

        # Test with single indicator (should not be enough)
        text = "This is a special offer"
        self.assertFalse(self.detector.is_advertisement(text))

    def test_get_ad_indicators_found(self):
        # Test with multiple indicators
        text = "Special offer! Limited time discount on our products. Buy now!"
        found = self.detector.get_ad_indicators_found(text)
        self.assertIn('special offer', found)
        self.assertIn('limited time', found)
        self.assertIn('buy now', found)

        # Test with no indicators
        text = "Hello, how are you? Just checking in."
        self.assertEqual(len(self.detector.get_ad_indicators_found(text)), 0)

        # Test with case insensitivity
        text = "SPECIAL OFFER! LIMITED TIME!"
        found = self.detector.get_ad_indicators_found(text)
        self.assertIn('special offer', found)
        self.assertIn('limited time', found) 