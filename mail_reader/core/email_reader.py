"""
Main email reader class that handles POP3 connection and email processing
"""
import os
import poplib
import ssl
import logging
import email
from datetime import datetime
from multiprocessing import Pool, cpu_count, Manager
from dotenv import load_dotenv
from .email_processor import EmailProcessor
import pathlib

# Load environment variables
load_dotenv()

class EmailReader:
    def __init__(self, contacts_file='email_contacts.csv', stats_file='email_stats.json'):
        self.host = os.getenv('EMAIL_HOST')
        self.port = int(os.getenv('EMAIL_PORT'))
        self.username = os.getenv('EMAIL_USER')
        self.password = os.getenv('EMAIL_PASSWORD')
        self.spam_folder = os.getenv('SPAM_FOLDER', os.path.join(os.path.expanduser("~"), "MailReader", "spam"))
        self.processor = EmailProcessor(contacts_file, stats_file)
        self.num_processes = max(1, cpu_count() - 1)
        self.update_callback = None
        self.manager = Manager()
        self.shared_queue = self.manager.Queue()
        self.delete_spam = True  # Default to True, can be changed via web UI

    def set_update_callback(self, callback):
        """Set callback function for processing updates"""
        self.update_callback = callback

    def _fetch_email(self, server, msg_num):
        """Fetch a single email from the server"""
        try:
            response, lines, octets = server.retr(msg_num)
            msg_content = b'\n'.join(lines).decode('utf-8')
            return email.message_from_string(msg_content)
        except Exception as e:
            logging.error(f"Error fetching email {msg_num}: {str(e)}")
            return None

    def _store_spam_email(self, msg, msg_num):
        """Store spam email locally"""
        try:
            # Create a filename based on date and message number
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"spam_{date_str}_{msg_num}.eml"
            filepath = os.path.join(self.spam_folder, filename)
            
            # Write the email to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(msg.as_string())
            
            logging.info(f"Stored spam email: {filename}")
            return True
        except Exception as e:
            logging.error(f"Error storing spam email: {str(e)}")
            return False

    def _delete_email(self, server, msg_num):
        """Delete email from server"""
        try:
            server.dele(msg_num)
            logging.info(f"Deleted email {msg_num} from server")
            return True
        except Exception as e:
            logging.error(f"Error deleting email {msg_num}: {str(e)}")
            return False

    def _process_email_batch(self, email_data):
        """Process a batch of emails"""
        try:
            results = []
            for msg, msg_num in email_data:
                if msg is not None:
                    # Process the email
                    result = self.processor.process_email(msg)
                    
                    # Extract relevant information for the update
                    if result:
                        email_info = {
                            'sender': msg.get('From', ''),
                            'subject': msg.get('Subject', ''),
                            'date': msg.get('Date', ''),
                            'is_ad': result.get('is_advertisement', False),
                            'unsubscribe_url': result.get('unsubscribe_url', None)
                        }
                        
                        # Handle spam emails if deletion is enabled
                        if self.delete_spam and email_info['is_ad']:
                            # Store spam locally
                            if self._store_spam_email(msg, msg_num):
                                email_info['stored_locally'] = True
                            else:
                                email_info['stored_locally'] = False
                        
                        # Put the update in the shared queue
                        self.shared_queue.put(email_info)
                        results.append((email_info, msg_num))
            return results
        except Exception as e:
            logging.error(f"Error processing email batch: {str(e)}")
            return []

    def _monitor_progress(self):
        """Monitor progress and call the update callback"""
        while True:
            try:
                # Get update from queue
                email_info = self.shared_queue.get()
                
                # Call the callback if set
                if self.update_callback:
                    self.update_callback(email_info)
                    
            except Exception as e:
                logging.error(f"Error in progress monitoring: {str(e)}")
                break

    def process_emails(self, num_emails=10):
        """Process emails in parallel with progress updates"""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to POP3 server
            server = poplib.POP3_SSL(self.host, self.port, context=context)
            server.user(self.username)
            server.pass_(self.password)

            # Get number of messages
            num_messages = len(server.list()[1])
            end = min(num_emails, num_messages)

            # Fetch all emails first
            emails = []
            for i in range(1, end + 1):
                msg = self._fetch_email(server, i)
                if msg is not None:
                    emails.append((msg, i))

            # Start progress monitoring in a separate thread
            from threading import Thread
            monitor_thread = Thread(target=self._monitor_progress)
            monitor_thread.daemon = True
            monitor_thread.start()

            # Split emails into batches for parallel processing
            batch_size = max(1, len(emails) // self.num_processes)
            email_batches = [emails[i:i + batch_size] for i in range(0, len(emails), batch_size)]

            # Process batches in parallel
            with Pool(processes=self.num_processes) as pool:
                results = pool.map(self._process_email_batch, email_batches)

            # Delete spam emails from server if enabled
            if self.delete_spam:
                for batch_results in results:
                    for email_info, msg_num in batch_results:
                        if email_info['is_ad'] and email_info.get('stored_locally', False):
                            self._delete_email(server, msg_num)

            server.quit()

            # Save state
            self.processor.save_state()

            # Log summary
            stats = self.processor.get_statistics()
            logging.info(f"Processing complete. Processed {len(emails)} emails.")
            logging.info(f"Total unique senders: {stats['unique_senders']}")
            logging.info(f"Advertisement rate: {stats['advertisement_rate']:.2f}%")

        except Exception as e:
            logging.error(f"Error connecting to email server: {str(e)}")

    def get_statistics(self):
        """Get current email statistics"""
        return self.processor.get_statistics() 