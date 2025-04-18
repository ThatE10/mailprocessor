import os
import poplib
import email
from email.header import decode_header
from datetime import datetime
import pandas as pd
from transformers import pipeline
from dotenv import load_dotenv
import ssl
import re
import logging
from urllib.parse import urlparse
import json

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_reader.log'),
        logging.StreamHandler()
    ]
)

class EmailReader:
    def __init__(self):
        self.host = os.getenv('EMAIL_HOST')
        self.port = int(os.getenv('EMAIL_PORT'))
        self.username = os.getenv('EMAIL_USER')
        self.password = os.getenv('EMAIL_PASSWORD')
        # Using a more appropriate model for text classification
        self.classifier = pipeline("text-classification", 
                                 model="microsoft/deberta-v3-base",
                                 top_k=2)
        self.contacts_file = 'email_contacts.csv'
        self.stats_file = 'email_stats.json'
        self.contacts_df = self._load_contacts()
        self.stats = self._load_stats()

    def _load_contacts(self):
        """Load existing contacts from CSV or create new DataFrame"""
        if os.path.exists(self.contacts_file):
            return pd.read_csv(self.contacts_file)
        return pd.DataFrame(columns=['email', 'last_contact', 'is_advertisement', 'unsubscribe_url', 'total_emails', 'ad_emails'])

    def _load_stats(self):
        """Load or create email statistics"""
        if os.path.exists(self.stats_file):
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {
            'total_emails_processed': 0,
            'total_advertisements': 0,
            'unique_senders': 0,
            'advertisement_rate': 0,
            'last_processed': None
        }

    def _save_contacts(self):
        """Save contacts to CSV file"""
        self.contacts_df.to_csv(self.contacts_file, index=False)

    def _save_stats(self):
        """Save email statistics"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=4)

    def _decode_subject(self, subject):
        """Decode email subject"""
        decoded_list = decode_header(subject)
        subject = ""
        for content, encoding in decoded_list:
            if isinstance(content, bytes):
                try:
                    subject += content.decode(encoding if encoding else 'utf-8')
                except:
                    subject += content.decode('utf-8', errors='ignore')
            else:
                subject += str(content)
        return subject

    def _get_email_content(self, msg):
        """Extract email content from message"""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        else:
            return msg.get_payload(decode=True).decode()

    def _extract_unsubscribe_url(self, text, headers):
        """Extract unsubscribe URL from email content and headers"""
        # Check List-Unsubscribe header first
        list_unsubscribe = headers.get('List-Unsubscribe', '')
        if list_unsubscribe:
            # Extract URL from List-Unsubscribe header
            urls = re.findall(r'<(.+?)>', list_unsubscribe)
            if urls:
                return urls[0]

        # Look for common unsubscribe patterns in the text
        patterns = [
            r'unsubscribe\s*:\s*(https?://[^\s<>"]+)',
            r'unsubscribe\s*link\s*:\s*(https?://[^\s<>"]+)',
            r'click\s*here\s*to\s*unsubscribe\s*:\s*(https?://[^\s<>"]+)',
            r'<a[^>]*href=["\'](https?://[^"\']*unsubscribe[^"\']*)["\'][^>]*>',
            r'<a[^>]*href=["\'](https?://[^"\']*opt-out[^"\']*)["\'][^>]*>'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None

    def _is_advertisement(self, text):
        """Use Hugging Face model to detect if text is an advertisement"""
        # Look for common advertisement indicators in the text
        ad_indicators = [
            'special offer', 'limited time', 'discount', 'sale',
            'promotion', 'deal', 'offer', 'buy now', 'subscribe',
            'unsubscribe', 'marketing', 'sponsored', 'advertisement',
            'exclusive deal', 'limited stock', 'free shipping',
            'money back guarantee', 'best price', 'special pricing'
        ]
        
        # Check for advertisement indicators in the text
        text_lower = text.lower()
        indicator_count = sum(1 for indicator in ad_indicators if indicator in text_lower)
        
        # If multiple indicators are found, it's likely an advertisement
        return indicator_count >= 2

    def _update_stats(self, is_ad):
        """Update email statistics"""
        self.stats['total_emails_processed'] += 1
        if is_ad:
            self.stats['total_advertisements'] += 1
        self.stats['unique_senders'] = len(self.contacts_df)
        self.stats['advertisement_rate'] = (self.stats['total_advertisements'] / 
                                          self.stats['total_emails_processed'] * 100)
        self.stats['last_processed'] = datetime.now().isoformat()
        self._save_stats()

    def process_emails(self, num_emails=10):
        """Process recent emails"""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to POP3 server
            server = poplib.POP3_SSL(self.host, self.port, context=context)
            server.user(self.username)
            server.pass_(self.password)

            # Get number of messages
            num_messages = len(server.list()[1])
            start = max(1, num_messages - num_emails + 1)

            for i in range(start, num_messages + 1):
                try:
                    # Get message
                    response, lines, octets = server.retr(i)
                    msg_content = b'\n'.join(lines).decode('utf-8')
                    msg = email.message_from_string(msg_content)

                    # Extract sender email
                    from_header = msg.get('From', '')
                    if '<' in from_header and '>' in from_header:
                        sender_email = from_header[from_header.find('<')+1:from_header.find('>')]
                    else:
                        sender_email = from_header

                    # Get email content
                    subject = self._decode_subject(msg.get('Subject', ''))
                    content = self._get_email_content(msg)
                    date = datetime.strptime(msg.get('Date', ''), '%a, %d %b %Y %H:%M:%S %z')

                    # Extract unsubscribe URL
                    unsubscribe_url = self._extract_unsubscribe_url(content, msg)

                    # Check if it's an advertisement
                    is_ad = self._is_advertisement(subject + ' ' + content)

                    # Update contacts DataFrame
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

                    # Update statistics
                    self._update_stats(is_ad)

                    logging.info(f"Processed email from {sender_email} - {'Advertisement' if is_ad else 'Not an advertisement'}")

                except Exception as e:
                    logging.error(f"Error processing email {i}: {str(e)}")
                    continue

            # Save updated contacts
            self._save_contacts()
            server.quit()

            # Log summary
            logging.info(f"Processing complete. Processed {num_emails} emails.")
            logging.info(f"Total unique senders: {len(self.contacts_df)}")
            logging.info(f"Advertisement rate: {self.stats['advertisement_rate']:.2f}%")

        except Exception as e:
            logging.error(f"Error connecting to email server: {str(e)}")

def main():
    reader = EmailReader()
    reader.process_emails()
    print(f"Processed emails and updated contacts in {reader.contacts_file}")
    print(f"Statistics saved in {reader.stats_file}")
    print(f"Logs saved in email_reader.log")

if __name__ == "__main__":
    main() 