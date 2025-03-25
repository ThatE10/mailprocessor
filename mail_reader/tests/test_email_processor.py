"""
Unit tests for EmailProcessor
"""
import unittest
import email
import pandas as pd
import os
import tempfile
from datetime import datetime
from ..core.email_processor import EmailProcessor

class TestEmailProcessor(unittest.TestCase):
    def setUp(self):
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.contacts_file = os.path.join(self.temp_dir, 'test_contacts.csv')
        self.stats_file = os.path.join(self.temp_dir, 'test_stats.json')
        self.processor = EmailProcessor(self.contacts_file, self.stats_file)

    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.contacts_file):
            os.remove(self.contacts_file)
        if os.path.exists(self.stats_file):
            os.remove(self.stats_file)
        os.rmdir(self.temp_dir)

    def test_process_new_email(self):
        """Test processing a new email from a new sender"""
        # Create test email
        msg = email.message_from_string("""
From: test@example.com
Subject: Test Subject
Date: Mon, 25 Mar 2024 10:00:00 +0000

This is a test email with special offer and limited time discount.
""")

        # Process email
        success = self.processor.process_email(msg)
        self.assertTrue(success)

        # Check contacts DataFrame
        self.assertEqual(len(self.processor.contacts_df), 1)
        contact = self.processor.contacts_df.iloc[0]
        self.assertEqual(contact['email'], 'test@example.com')
        self.assertEqual(contact['total_emails'], 1)
        self.assertEqual(contact['ad_emails'], 1)
        self.assertTrue(contact['is_advertisement'])

    def test_process_existing_sender(self):
        """Test processing an email from an existing sender"""
        # Create initial email
        msg1 = email.message_from_string("""
From: test@example.com
Subject: Test Subject
Date: Mon, 25 Mar 2024 10:00:00 +0000

This is a test email.
""")
        self.processor.process_email(msg1)

        # Create second email from same sender
        msg2 = email.message_from_string("""
From: test@example.com
Subject: Special Offer
Date: Mon, 25 Mar 2024 11:00:00 +0000

This is an advertisement with special offer and limited time.
""")
        self.processor.process_email(msg2)

        # Check contacts DataFrame
        self.assertEqual(len(self.processor.contacts_df), 1)
        contact = self.processor.contacts_df.iloc[0]
        self.assertEqual(contact['email'], 'test@example.com')
        self.assertEqual(contact['total_emails'], 2)
        self.assertEqual(contact['ad_emails'], 1)
        self.assertTrue(contact['is_advertisement'])

    def test_save_and_load_state(self):
        """Test saving and loading processor state"""
        # Process an email
        msg = email.message_from_string("""
From: test@example.com
Subject: Test Subject
Date: Mon, 25 Mar 2024 10:00:00 +0000

This is a test email.
""")
        self.processor.process_email(msg)

        # Save state
        self.processor.save_state()

        # Create new processor instance
        new_processor = EmailProcessor(self.contacts_file, self.stats_file)

        # Check if state was loaded correctly
        self.assertEqual(len(new_processor.contacts_df), 1)
        self.assertEqual(new_processor.contacts_df.iloc[0]['email'], 'test@example.com')

    def test_get_statistics(self):
        """Test getting email statistics"""
        # Process some emails
        msg1 = email.message_from_string("""
From: test1@example.com
Subject: Test Subject
Date: Mon, 25 Mar 2024 10:00:00 +0000

This is a test email.
""")
        msg2 = email.message_from_string("""
From: test2@example.com
Subject: Special Offer
Date: Mon, 25 Mar 2024 11:00:00 +0000

This is an advertisement with special offer and limited time.
""")

        self.processor.process_email(msg1)
        self.processor.process_email(msg2)

        # Check statistics
        stats = self.processor.get_statistics()
        self.assertEqual(stats['total_emails_processed'], 2)
        self.assertEqual(stats['total_advertisements'], 1)
        self.assertEqual(stats['unique_senders'], 2)
        self.assertEqual(stats['advertisement_rate'], 50.0) 