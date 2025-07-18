"""
Core email processing functionality
"""
import os
from datetime import datetime
import pandas as pd
import logging
from ..utils.email_parser import EmailParser
from ..utils.ad_detector import AdvertisementDetector
from ..utils.stats_manager import StatsManager

class EmailProcessor:
    def __init__(self, contacts_file='email_contacts.csv', stats_file='email_stats.json'):
        self.contacts_file = contacts_file
        self.contacts_df = self._load_contacts()
        self.email_parser = EmailParser()
        self.ad_detector = AdvertisementDetector()
        self.stats_manager = StatsManager(stats_file)

    def _load_contacts(self):
        """Load existing contacts from CSV or create new DataFrame"""
        if os.path.exists(self.contacts_file):
            return pd.read_csv(self.contacts_file)
        return pd.DataFrame(columns=[
            'email', 'last_contact', 'is_advertisement', 
            'unsubscribe_url', 'total_emails', 'ad_emails'
        ])

    def _save_contacts(self):
        """Save contacts to CSV file"""
        self.contacts_df.to_csv(self.contacts_file, index=False)

    def process_email(self, msg):
        """Process a single email message"""
        try:
            # Extract email information
            sender_email = self.email_parser.get_sender_email(msg)
            subject = self.email_parser.decode_subject(msg.get('Subject', ''))
            content = self.email_parser.get_email_content(msg)
            date = datetime.strptime(msg.get('Date', ''), '%a, %d %b %Y %H:%M:%S %z')
            unsubscribe_url = self.email_parser.extract_unsubscribe_url(content, msg)

            # Check if it's an advertisement
            is_ad = self.ad_detector.is_advertisement(subject + ' ' + content)

            # Update contacts DataFrame
            self._update_contacts(sender_email, date, is_ad, unsubscribe_url)

            # Update statistics
            self.stats_manager.update_stats(is_ad)

            logging.info(f"Processed email from {sender_email} - {'Advertisement' if is_ad else 'Not an advertisement'}")
            
            # Return processing results
            return {
                'sender': sender_email,
                'subject': subject,
                'date': date.isoformat(),
                'is_advertisement': is_ad,
                'unsubscribe_url': unsubscribe_url
            }

        except Exception as e:
            logging.error(f"Error processing email: {str(e)}")
            return None

    def _update_contacts(self, sender_email, date, is_ad, unsubscribe_url):
        """Update contacts DataFrame with new email information"""
        if sender_email not in self.contacts_df['email'].values:
            self.contacts_df = pd.concat([self.contacts_df, pd.DataFrame({
                'email': [sender_email],
                'last_contact': [date],
                'is_advertisement': [is_ad],
                'unsubscribe_url': [unsubscribe_url],
                'total_emails': [1],
                'ad_emails': [1 if is_ad else 0]
            })], ignore_index=True)
        else:
            mask = self.contacts_df['email'] == sender_email
            self.contacts_df.loc[mask, 'last_contact'] = date
            self.contacts_df.loc[mask, 'is_advertisement'] = is_ad
            if unsubscribe_url:
                self.contacts_df.loc[mask, 'unsubscribe_url'] = unsubscribe_url
            self.contacts_df.loc[mask, 'total_emails'] += 1
            if is_ad:
                self.contacts_df.loc[mask, 'ad_emails'] += 1

    def get_statistics(self):
        """Get current email statistics"""
        return {
            'total_emails_processed': self.stats_manager.stats['total_emails_processed'],
            'total_advertisements': self.stats_manager.stats['total_advertisements'],
            'unique_senders': len(self.contacts_df),
            'advertisement_rate': self.stats_manager.stats['advertisement_rate'],
            'last_processed': self.stats_manager.stats['last_processed']
        }

    def save_state(self):
        """Save current state to files"""
        self._save_contacts()
        self.stats_manager.save_stats() 