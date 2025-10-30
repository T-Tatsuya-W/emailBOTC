"""
Email Handler - Isolated email functionality for sending and receiving emails.

This module provides a simple interface for:
1. Sending emails
2. Waiting for and receiving responses from specific recipients with specific subjects
"""
import os
import time
import imaplib
import smtplib
import re
from typing import Optional, Dict
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parseaddr
import email as email_lib
from dotenv import load_dotenv

load_dotenv()


class EmailHandler:
    """
    Handles email sending and receiving with response tracking.
    
    This class provides a unified interface for email operations including
    sending emails and waiting for responses from specific recipients.
    """
    
    def __init__(self, poll_interval: int = 5, timeout: int = 30):
        """
        Initialize the EmailHandler.
        
        Args:
            poll_interval: Seconds to wait between checking for new emails (default: 5)
            timeout: Timeout in seconds for SMTP operations (default: 30)
        """
        self.poll_interval = poll_interval
        self.smtp_timeout = timeout
        self.imap_connection = None
        
        # Load email credentials from environment
        self.email_address = self._get_email_address()
        self.email_password = self._get_email_password()
        self.smtp_host = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER") or "smtp.gmail.com"
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.imap_host = os.getenv("IMAP_HOST") or os.getenv("IMAP_SERVER") or "imap.gmail.com"
        self.imap_port = int(os.getenv("IMAP_PORT") or os.getenv("IMAP_SSL_PORT") or "993")
    
    def _get_email_address(self) -> str:
        """Get email address from environment variables."""
        return (
            os.getenv("IMAP_USER")
            or os.getenv("IMAP_USERNAME")
            or os.getenv("IMAP_EMAIL")
            or os.getenv("EMAIL_ADDRESS")
        )
    
    def _get_email_password(self) -> str:
        """Get email password from environment variables."""
        return (
            os.getenv("IMAP_PASS")
            or os.getenv("IMAP_PASSWORD")
            or os.getenv("IMAP_PWD")
            or os.getenv("EMAIL_PASSWORD")
        )
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send an email to a recipient.
        
        Args:
            to_email: Recipient's email address
            subject: Email subject line
            body: Email body text (plain text)
        
        Returns:
            True if email was sent successfully, False otherwise
        
        Raises:
            ValueError: If email credentials are not configured
            smtplib.SMTPException: If sending fails
        """
        if not self.email_address or not self.email_password:
            raise ValueError(
                "Email credentials not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD "
                "environment variables or provide IMAP_USER/IMAP_PASS credentials."
            )
        
        try:
            # Create the message
            msg = MIMEText(body or "", _subtype="plain", _charset="utf-8")
            msg["From"] = self.email_address
            msg["To"] = to_email
            msg["Subject"] = subject or ""
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.smtp_timeout) as smtp:
                smtp.ehlo()
                try:
                    smtp.starttls()
                    smtp.ehlo()
                except Exception:
                    pass  # If STARTTLS fails, continue (may fail at login)
                
                smtp.login(self.email_address, self.email_password)
                smtp.send_message(msg)
            
            return True
            
        except Exception as e:
            raise smtplib.SMTPException(f"Failed to send email: {e}")
    
    def wait_for_response(
        self, 
        from_email: str, 
        expected_subject: str,
        timeout_seconds: Optional[int] = None,
        mark_as_read: bool = True
    ) -> Optional[Dict[str, str]]:
        """
        Send an email and wait for a response from a specific recipient with a specific subject.
        
        Args:
            from_email: Email address of the expected sender
            expected_subject: Expected subject line (will be normalized to ignore Re:/Fw: prefixes)
            timeout_seconds: Maximum time to wait for response in seconds (None = wait indefinitely)
            mark_as_read: Whether to mark the message as read once received (default: True)
        
        Returns:
            Dictionary with keys 'from', 'subject', 'body', 'uid' if response found, None if timeout
        
        Raises:
            ValueError: If email credentials are not configured
            SystemExit: If IMAP connection fails
        """
        if not self.email_address or not self.email_password:
            raise ValueError(
                "Email credentials not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD "
                "environment variables or provide IMAP_USER/IMAP_PASS credentials."
            )
        
        # Connect to IMAP
        imap = self._connect_imap()
        
        # Normalize the expected subject
        normalized_expected = self._normalize_subject(expected_subject)
        
        start_time = time.time()
        check_count = 0
        
        try:
            while True:
                check_count += 1
                elapsed = time.time() - start_time
                
                # Refresh connection to get latest messages from server
                try:
                    imap.noop()
                except Exception as e:
                    print(f"Warning: IMAP noop failed: {e}")
                
                # Fetch unseen messages
                messages = self._fetch_unseen_messages(imap)
                
                if check_count == 1:
                    print(f"Starting to wait for response from {from_email}")
                    print(f"  Expected subject (normalized): '{normalized_expected}'")
                    print(f"  Poll interval: {self.poll_interval}s")
                    if timeout_seconds:
                        print(f"  Timeout: {timeout_seconds}s")
                
                if check_count % 5 == 0:  # Print status every 5 checks
                    print(f"Still waiting... (checked {check_count} times, {elapsed:.1f}s elapsed)")
                
                for msg in messages:
                    msg_from = (msg.get('from') or '').strip().lower()
                    msg_subject = msg.get('subject') or ''
                    msg_body = msg.get('body') or ''
                    msg_uid = msg.get('uid')
                    
                    # Debug: print all messages being checked
                    normalized_subject = self._normalize_subject(msg_subject)
                    print(f"  Checking message from: {msg_from}, subject: '{normalized_subject}'")
                    
                    # Check if this message is from the expected sender
                    if msg_from == from_email.strip().lower():
                        # Check if subject matches (normalized)
                        if normalized_subject == normalized_expected:
                            # Found the response!
                            print(f"✓ Found matching response!")
                            if mark_as_read:
                                self._mark_seen(imap, msg_uid)
                            
                            return {
                                'from': msg.get('from'),
                                'subject': msg_subject,
                                'body': msg_body,
                                'uid': msg_uid
                            }
                        else:
                            # Not the right subject, mark as seen to avoid re-processing
                            print(f"  → Subject doesn't match (expected '{normalized_expected}', got '{normalized_subject}')")
                            if mark_as_read:
                                self._mark_seen(imap, msg_uid)
                    else:
                        # Not from the expected sender, mark as seen
                        print(f"  → Sender doesn't match (expected '{from_email.strip().lower()}')")
                        if mark_as_read:
                            self._mark_seen(imap, msg_uid)
                
                # Check timeout AFTER checking messages
                if timeout_seconds and (time.time() - start_time) > timeout_seconds:
                    print(f"✗ Timeout reached after {elapsed:.1f}s ({check_count} checks)")
                    return None
                
                # Wait before checking again
                time.sleep(self.poll_interval)
                
        finally:
            self._close_imap(imap)
    
    def send_and_wait_for_response(
        self,
        to_email: str,
        subject: str,
        body: str,
        timeout_seconds: Optional[int] = None,
        mark_as_read: bool = True
    ) -> Optional[Dict[str, str]]:
        """
        Send an email and wait for a response from the recipient with the same subject.
        
        Args:
            to_email: Recipient's email address
            subject: Email subject line
            body: Email body text
            timeout_seconds: Maximum time to wait for response in seconds (None = wait indefinitely)
            mark_as_read: Whether to mark the response as read once received (default: True)
        
        Returns:
            Dictionary with keys 'from', 'subject', 'body', 'uid' if response received, None if timeout
        
        Raises:
            ValueError: If email credentials are not configured
            smtplib.SMTPException: If sending fails
            SystemExit: If IMAP connection fails
        """
        # Send the email first
        print(f"Sending email to {to_email}")
        print(f"  Subject: {subject}")
        self.send_email(to_email, subject, body)
        print(f"✓ Email sent successfully")
        
        # Give the email server a moment to process the sent email
        # This helps avoid timing issues where we check for response too quickly
        print(f"Waiting {self.poll_interval}s before checking for responses...")
        time.sleep(self.poll_interval)
        
        # Wait for response
        return self.wait_for_response(to_email, subject, timeout_seconds, mark_as_read)
    
    def _connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server and select INBOX."""
        try:
            imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            imap.login(self.email_address, self.email_password)
            imap.select("INBOX")
            return imap
        except Exception as exc:
            raise SystemExit(f"IMAP connection failed: {exc}")
    
    def _fetch_unseen_messages(self, imap: imaplib.IMAP4_SSL) -> list:
        """
        Fetch all unseen messages from INBOX.
        
        Returns:
            List of dictionaries with keys: 'uid', 'from', 'subject', 'body'
        """
        messages = []
        
        try:
            status, data = imap.uid('search', None, 'UNSEEN')
            
            if status != "OK" or not data or not data[0]:
                return messages
            
            for uid_bytes in data[0].split():
                uid = uid_bytes.decode() if isinstance(uid_bytes, bytes) else str(uid_bytes)
                status, fetch_data = imap.uid('fetch', uid, '(RFC822)')
                
                if status != "OK" or not fetch_data:
                    continue
                
                raw = fetch_data[0][1]
                if not raw:
                    continue
                
                msg = email_lib.message_from_bytes(raw)
                from_addr = parseaddr(self._decode_header(msg.get("From")))[1]
                subject = self._decode_header(msg.get("Subject"))
                body = self._extract_body(msg)
                
                messages.append({
                    "uid": uid,
                    "from": from_addr,
                    "subject": subject,
                    "body": body
                })
        
        except Exception as exc:
            print(f"Error fetching messages: {exc}")
        
        return messages
    
    def _mark_seen(self, imap: imaplib.IMAP4_SSL, uid: str) -> None:
        """Mark a message as seen by UID."""
        try:
            imap.uid('store', uid, '+FLAGS', '(\\Seen)')
        except Exception:
            pass
    
    def _close_imap(self, imap: imaplib.IMAP4_SSL) -> None:
        """Close IMAP connection."""
        if imap:
            try:
                imap.logout()
            except Exception:
                pass
    
    @staticmethod
    def _decode_header(value: Optional[str]) -> str:
        """Decode a possibly MIME-encoded header value to a unicode string."""
        if value is None:
            return ""
        
        parts = decode_header(value)
        decoded = ""
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded += part.decode(enc or "utf-8", errors="replace")
            else:
                decoded += part
        return decoded
    
    @staticmethod
    def _extract_body(msg: email_lib.message.Message) -> str:
        """Extract plain text body from email message."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition") or "")
                
                if ctype == "text/plain" and "attachment" not in disp:
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body = payload.decode(charset, errors="replace")
                    except Exception:
                        body = payload.decode("utf-8", errors="replace")
                    break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                try:
                    body = payload.decode(charset, errors="replace")
                except Exception:
                    body = payload.decode("utf-8", errors="replace")
        
        return body
    
    @staticmethod
    def _normalize_subject(subject: Optional[str]) -> str:
        """
        Normalize subject by stripping common reply/forward prefixes and converting to lowercase.
        
        This allows matching subjects like "Test" with "Re: Test" or "Fw: Re: Test"
        """
        if not subject:
            return ""
        
        s = subject.strip()
        prefix_re = re.compile(r'^(?:\s*(?:re|fw|fwd)\s*[:\-]\s*)+', flags=re.IGNORECASE)
        s = prefix_re.sub("", s).strip()
        return s.lower()


# Convenience function for simple use cases
def send_email_and_get_response(
    to_email: str,
    subject: str,
    body: str,
    timeout_seconds: Optional[int] = None,
    poll_interval: int = 5
) -> Optional[Dict[str, str]]:
    """
    Convenience function to send an email and wait for a response.
    
    Args:
        to_email: Recipient's email address
        subject: Email subject line
        body: Email body text
        timeout_seconds: Maximum time to wait for response in seconds (None = wait indefinitely)
        poll_interval: Seconds between checking for new emails (default: 5)
    
    Returns:
        Dictionary with keys 'from', 'subject', 'body', 'uid' if response received, None if timeout
    
    Example:
        >>> response = send_email_and_get_response(
        ...     "user@example.com",
        ...     "Question for you",
        ...     "What is your answer?",
        ...     timeout_seconds=300  # Wait up to 5 minutes
        ... )
        >>> if response:
        ...     print(f"Response: {response['body']}")
    """
    handler = EmailHandler(poll_interval=poll_interval)
    return handler.send_and_wait_for_response(to_email, subject, body, timeout_seconds)


if __name__ == "__main__":
    # Example usage
    print("Email Handler - Example Usage")
    print("=" * 60)
    
    # Example 1: Simple send
    try:
        handler = EmailHandler()
        recipient = os.getenv("DEFAULT_PLAYER_EMAIL", "test@example.com")
        
        print(f"\nExample 1: Sending email to {recipient}")
        handler.send_email(
            recipient,
            "Test Email",
            "This is a test email from email_handler.py"
        )
        print("✓ Email sent successfully")
    except Exception as e:
        print(f"✗ Failed to send email: {e}")
    
    # Example 2: Send and wait for response
    print("\nExample 2: Send and wait for response")
    print("This will wait indefinitely for a response...")
    print("(Press Ctrl+C to cancel)")
    
    try:
        response = send_email_and_get_response(
            recipient,
            "Please Reply",
            "Please reply to this email to test the response functionality.",
            timeout_seconds=300  # Wait up to 5 minutes
        )
        
        if response:
            print(f"✓ Response received from {response['from']}")
            print(f"  Subject: {response['subject']}")
            print(f"  Body: {response['body'][:100]}...")
        else:
            print("✗ No response received within timeout period")
    
    except KeyboardInterrupt:
        print("\n✗ Cancelled by user")
    except Exception as e:
        print(f"✗ Error: {e}")
