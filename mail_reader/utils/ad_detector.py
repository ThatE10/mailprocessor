"""
Advertisement detection utilities
"""
from transformers import pipeline

class AdvertisementDetector:
    def __init__(self):
        self.classifier = pipeline("text-classification", 
                                 model="microsoft/deberta-v3-base",
                                 top_k=2)
        self.ad_indicators = [
            'special offer', 'limited time', 'discount', 'sale',
            'promotion', 'deal', 'offer', 'buy now', 'subscribe',
            'unsubscribe', 'marketing', 'sponsored', 'advertisement',
            'exclusive deal', 'limited stock', 'free shipping',
            'money back guarantee', 'best price', 'special pricing'
        ]

    def is_advertisement(self, text):
        """Detect if text is an advertisement"""
        # Check for advertisement indicators in the text
        text_lower = text.lower()
        indicator_count = sum(1 for indicator in self.ad_indicators 
                            if indicator in text_lower)
        
        # If multiple indicators are found, it's likely an advertisement
        return indicator_count >= 2

    def get_ad_indicators_found(self, text):
        """Get list of advertisement indicators found in text"""
        text_lower = text.lower()
        return [indicator for indicator in self.ad_indicators 
                if indicator in text_lower] 