"""
Email parsing utilities
"""
import email
from email.header import decode_header
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class EmailParser:
    def get_sender_email(self, msg):
        """Extract sender email from message"""
        from_header = msg.get('From', '')
        if '<' in from_header and '>' in from_header:
            return from_header[from_header.find('<')+1:from_header.find('>')]
        return from_header

    def decode_subject(self, subject):
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

    def get_email_content(self, msg):
        """Extract email content from message"""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
                elif part.get_content_type() == "text/html":
                    return part.get_payload(decode=True).decode()
        else:
            return msg.get_payload(decode=True).decode()

    def _extract_urls_from_html(self, html_content):
        """Extract URLs from HTML content using Beautiful Soup"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = []
        
        # Look for links with unsubscribe-related text
        unsubscribe_keywords = [
            'unsubscribe', 'opt-out', 'opt out', 'remove me',
            'unsubscribe me', 'stop receiving', 'manage preferences'
        ]
        
        for link in soup.find_all('a'):
            # Get link text and href
            link_text = link.get_text().lower()
            href = link.get('href')
            
            if href:
                # Check if link text contains unsubscribe keywords
                if any(keyword in link_text for keyword in unsubscribe_keywords):
                    urls.append(href)
                # Also check if href contains unsubscribe keywords
                elif any(keyword in href.lower() for keyword in unsubscribe_keywords):
                    urls.append(href)
        
        return urls

    def _extract_urls_from_text(self, text):
        """Extract URLs from plain text using regex"""
        # Look for URLs in text that contain unsubscribe-related words
        patterns = [
            r'(?:unsubscribe|opt-out|opt out|remove me|unsubscribe me|stop receiving|manage preferences)\s*:\s*(https?://[^\s<>"]+)',
            r'(https?://[^\s<>"]*?(?:unsubscribe|opt-out|opt out|remove me|unsubscribe me|stop receiving|manage preferences)[^\s<>"]*)'
        ]
        
        urls = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.extend(matches)
        
        return urls

    def extract_unsubscribe_url(self, text, headers):
        """Extract unsubscribe URL from email content and headers"""
        # First check List-Unsubscribe header
        list_unsubscribe = headers.get('List-Unsubscribe', '')
        if list_unsubscribe:
            urls = re.findall(r'<(.+?)>', list_unsubscribe)
            if urls:
                return urls[0]

        # Try to extract URLs from HTML content
        if '<html' in text.lower() or '<body' in text.lower():
            urls = self._extract_urls_from_html(text)
            if urls:
                return urls[0]

        # If no HTML or no URLs found in HTML, try plain text
        urls = self._extract_urls_from_text(text)
        if urls:
            return urls[0]

        return None 