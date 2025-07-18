import imaplib
import email
from email.header import decode_header
import re
import argparse
import sys
from tqdm import tqdm  # Ensure this is installed: pip install tqdm

IMAP_SERVER = 'imap.migadu.com'
MAILBOX = 'INBOX'

def clean_email(addr):
    match = re.search(r'<(.+?)>', addr)
    return match.group(1).lower() if match else addr.lower()

def get_unique_senders(email_account, email_password):
    unique_emails = set()

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(email_account, email_password)
        mail.select(MAILBOX)

        status, messages = mail.search(None, 'ALL')
        if status != 'OK':
            print("No messages found.")
            return []

        msg_nums = messages[0].split()
        for num in tqdm(msg_nums, desc="Processing emails", unit="msg"):
            status, msg_data = mail.fetch(num, '(RFC822)')
            if status != 'OK':
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            from_header = msg.get('From', '')
            decoded, charset = decode_header(from_header)[0]
            if isinstance(decoded, bytes):
                from_header = decoded.decode(charset or 'utf-8', errors='replace')
            else:
                from_header = decoded

            email_addr = clean_email(from_header)
            unique_emails.add(email_addr)

        mail.logout()
        return sorted(unique_emails)

    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract unique email senders from a Migadu mailbox.')
    parser.add_argument('--email', required=True, help='Your Migadu email address')
    parser.add_argument('--pass', required=True, dest='password', help='Your Migadu email password (or app password)')

    args = parser.parse_args()

    senders = get_unique_senders(args.email, args.password)
    for sender in senders:
        print(sender)
