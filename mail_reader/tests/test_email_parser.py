"""
Unit tests for EmailParser
"""
import unittest
import email
from ..utils.email_parser import EmailParser

class TestEmailParser(unittest.TestCase):
    def setUp(self):
        self.parser = EmailParser()

    def test_get_sender_email(self):
        """Test sender email extraction with various formats"""
        test_cases = [
            # Standard format with name and email
            ("From: John Doe <john@example.com>", "john@example.com"),
            # Simple email format
            ("From: john@example.com", "john@example.com"),
            # Multiple email addresses
            ("From: John Doe <john@example.com>, Jane Doe <jane@example.com>", "john@example.com"),
            # With display name containing special characters
            ("From: John Doe (Work) <john@example.com>", "john@example.com"),
            # With multiple angle brackets
            ("From: <<john@example.com>>", "john@example.com"),
            # Empty From header
            ("From: ", ""),
            # Malformed From header
            ("From: <invalid>", "<invalid>"),
        ]

        for header, expected in test_cases:
            msg = email.message_from_string(f"{header}\nSubject: Test")
            self.assertEqual(self.parser.get_sender_email(msg), expected)

    def test_decode_subject(self):
        """Test subject decoding with various encodings and formats"""
        test_cases = [
            # Simple subject
            ("Subject: Test Subject", "Test Subject"),
            # Base64 encoded subject
            ("Subject: =?utf-8?B?SGVsbG8gV29ybGQ=?=", "Hello World"),
            # Multiple encoded parts
            ("Subject: =?utf-8?B?SGVsbG8=?= =?utf-8?B?V29ybGQ=?=", "Hello World"),
            # Mixed encoded and plain text
            ("Subject: =?utf-8?B?SGVsbG8=?= World", "Hello World"),
            # Different character sets
            ("Subject: =?iso-8859-1?B?SGVsbG8gV29ybGQ=?=", "Hello World"),
            # Invalid encoding
            ("Subject: =?invalid?B?SGVsbG8=?=", "=?invalid?B?SGVsbG8=?="),
            # Empty subject
            ("Subject: ", ""),
            # No subject header
            ("", ""),
        ]

        for header, expected in test_cases:
            msg = email.message_from_string(f"{header}\nFrom: test@example.com")
            self.assertEqual(self.parser.decode_subject(msg.get('Subject', '')), expected)

    def test_get_email_content(self):
        """Test email content extraction with various formats"""
        test_cases = [
            # Plain text email
            ("""
Content-Type: text/plain

Hello World
            """, "Hello World"),

            # HTML email
            ("""
Content-Type: text/html

<html><body>Hello World</body></html>
            """, "<html><body>Hello World</body></html>"),

            # Multipart email with both plain and HTML
            ("""
Content-Type: multipart/mixed; boundary="boundary"

--boundary
Content-Type: text/plain

Plain text content
--boundary
Content-Type: text/html

<html><body>HTML content</body></html>
--boundary--
            """, "Plain text content"),  # Should prefer plain text

            # Multipart email with attachments
            ("""
Content-Type: multipart/mixed; boundary="boundary"

--boundary
Content-Type: text/plain

Hello World
--boundary
Content-Type: application/pdf

[PDF content]
--boundary--
            """, "Hello World"),

            # Nested multipart
            ("""
Content-Type: multipart/mixed; boundary="outer"

--outer
Content-Type: multipart/alternative; boundary="inner"

--inner
Content-Type: text/plain

Plain text
--inner
Content-Type: text/html

<html><body>HTML</body></html>
--inner--
--outer--
            """, "Plain text"),

            # Empty email
            ("""
Content-Type: text/plain

            """, ""),

            # Invalid content type
            ("""
Content-Type: invalid/type

Hello World
            """, "Hello World"),
        ]

        for email_content, expected in test_cases:
            msg = email.message_from_string(email_content)
            content = self.parser.get_email_content(msg)
            self.assertIn(expected, content)

    def test_extract_unsubscribe_url(self):
        """Test unsubscribe URL extraction with various formats and edge cases"""
        test_cases = [
            # List-Unsubscribe header tests
            {
                'headers': {"List-Unsubscribe": "<https://example.com/unsubscribe>"},
                'content': "",
                'expected': "https://example.com/unsubscribe"
            },
            {
                'headers': {"List-Unsubscribe": "<https://example.com/unsubscribe>, <mailto:unsubscribe@example.com>"},
                'content': "",
                'expected': "https://example.com/unsubscribe"
            },
            {
                'headers': {"List-Unsubscribe": "<mailto:unsubscribe@example.com>"},
                'content': "",
                'expected': None
            },

            # HTML content tests
            {
                'headers': {},
                'content': """
                <html>
                <body>
                <a href="https://example.com/unsubscribe">Click here to unsubscribe</a>
                </body>
                </html>
                """,
                'expected': "https://example.com/unsubscribe"
            },
            {
                'headers': {},
                'content': """
                <html>
                <body>
                <a href="https://example.com/opt-out">Manage preferences</a>
                </body>
                </html>
                """,
                'expected': "https://example.com/opt-out"
            },
            {
                'headers': {},
                'content': """
                <html>
                <body>
                <a href="https://example.com/stop">Stop receiving emails</a>
                </body>
                </html>
                """,
                'expected': "https://example.com/stop"
            },
            {
                'headers': {},
                'content': """
                <html>
                <body>
                <a href="https://example.com/unsubscribe" style="color: red;">Unsubscribe</a>
                <a href="https://example.com/other">Other link</a>
                </body>
                </html>
                """,
                'expected': "https://example.com/unsubscribe"
            },

            # Plain text tests
            {
                'headers': {},
                'content': "To unsubscribe, visit: https://example.com/unsubscribe",
                'expected': "https://example.com/unsubscribe"
            },
            {
                'headers': {},
                'content': "Click here to opt-out: https://example.com/opt-out",
                'expected': "https://example.com/opt-out"
            },
            {
                'headers': {},
                'content': "Manage your preferences: https://example.com/preferences",
                'expected': "https://example.com/preferences"
            },

            # Edge cases
            {
                'headers': {},
                'content': "Invalid URL: not-a-url",
                'expected': None
            },
            {
                'headers': {},
                'content': "URL without protocol: example.com/unsubscribe",
                'expected': None
            },
            {
                'headers': {},
                'content': "Multiple URLs: https://example.com/1 and https://example.com/2",
                'expected': "https://example.com/1"
            },
            {
                'headers': {},
                'content': "Malformed HTML: <a href='broken>Unsubscribe</a>",
                'expected': None
            },
        ]

        for test_case in test_cases:
            result = self.parser.extract_unsubscribe_url(test_case['content'], test_case['headers'])
            self.assertEqual(result, test_case['expected'])

    def test_extract_urls_from_html(self):
        """Test HTML URL extraction with various formats"""
        test_cases = [
            # Multiple unsubscribe links
            ("""
            <html>
            <body>
            <a href="https://example.com/unsubscribe">Unsubscribe</a>
            <a href="https://example.com/opt-out">Opt out</a>
            </body>
            </html>
            """, ["https://example.com/unsubscribe", "https://example.com/opt-out"]),

            # Links with unsubscribe in URL
            ("""
            <html>
            <body>
            <a href="https://example.com/unsubscribe-link">Click here</a>
            </body>
            </html>
            """, ["https://example.com/unsubscribe-link"]),

            # Links with unsubscribe in text
            ("""
            <html>
            <body>
            <a href="https://example.com/other">Click here to unsubscribe</a>
            </body>
            </html>
            """, ["https://example.com/other"]),

            # No unsubscribe links
            ("""
            <html>
            <body>
            <a href="https://example.com/other">Other link</a>
            </body>
            </html>
            """, []),

            # Malformed HTML
            ("""
            <html>
            <body>
            <a href="broken>Unsubscribe</a>
            </body>
            </html>
            """, []),
        ]

        for html_content, expected in test_cases:
            urls = self.parser._extract_urls_from_html(html_content)
            self.assertEqual(urls, expected)

    def test_extract_urls_from_text(self):
        """Test plain text URL extraction with various formats"""
        test_cases = [
            # Standard unsubscribe URL
            ("To unsubscribe, visit: https://example.com/unsubscribe",
             ["https://example.com/unsubscribe"]),

            # Multiple URLs
            ("Unsubscribe: https://example.com/1 or https://example.com/2",
             ["https://example.com/1", "https://example.com/2"]),

            # Different formats
            ("Click here to opt-out: https://example.com/opt-out",
             ["https://example.com/opt-out"]),

            # URLs with different protocols
            ("Manage preferences: http://example.com/prefs",
             ["http://example.com/prefs"]),

            # Invalid URLs
            ("Invalid URL: not-a-url", []),
            ("URL without protocol: example.com/unsubscribe", []),

            # URLs with special characters
            ("Unsubscribe: https://example.com/unsubscribe?user=123&type=email",
             ["https://example.com/unsubscribe?user=123&type=email"]),
        ]

        for text, expected in test_cases:
            urls = self.parser._extract_urls_from_text(text)
            self.assertEqual(urls, expected) 