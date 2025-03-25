"""
Statistics management utilities
"""
import json
from datetime import datetime

class StatsManager:
    def __init__(self, stats_file='email_stats.json'):
        self.stats_file = stats_file
        self.stats = self._load_stats()

    def _load_stats(self):
        """Load or create email statistics"""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'total_emails_processed': 0,
                'total_advertisements': 0,
                'unique_senders': 0,
                'advertisement_rate': 0,
                'last_processed': None
            }

    def save_stats(self):
        """Save email statistics"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=4)

    def update_stats(self, is_ad):
        """Update email statistics"""
        self.stats['total_emails_processed'] += 1
        if is_ad:
            self.stats['total_advertisements'] += 1
        self.stats['advertisement_rate'] = (self.stats['total_advertisements'] / 
                                          self.stats['total_emails_processed'] * 100)
        self.stats['last_processed'] = datetime.now().isoformat()
        self.save_stats()

    def get_stats(self):
        """Get current statistics"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics to initial values"""
        self.stats = {
            'total_emails_processed': 0,
            'total_advertisements': 0,
            'unique_senders': 0,
            'advertisement_rate': 0,
            'last_processed': None
        }
        self.save_stats() 