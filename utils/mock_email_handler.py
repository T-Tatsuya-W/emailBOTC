"""Mock EmailHandler for tests.

This mock implements the same public interface as `utils.email_handler.EmailHandler`
but performs no network I/O. It records sent messages and allows test code to
populate unread messages that `check_unread` will return. It also supports a
simple UID lookup to simulate reply-by-UID behavior.
"""
from typing import List, Dict, Optional, Any


class MockEmailHandler:
    """A drop-in mock of EmailHandler for unit tests.

    Usage:
      mock = MockEmailHandler(email_address="me@example.com")
      mock.add_unread({"id": "1", "uid": 101, "from": "a@b.com", "subject": "Hi", "date": "now", "body": "Hello", "clean_body": "Hello"})
      msgs = mock.check_unread()
      mock.send_email(to_address="x@y.com", subject="s", body="b")

    The mock records sent messages in `sent_messages` and supports a `messages_by_uid`
    mapping used when `send_email(..., reply_uid=...)` is invoked.
    """

    def __init__(
        self,
        email_address: Optional[str] = None,
        app_password: Optional[str] = None,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None,
    ) -> None:
        # Mirror the real handler constructor signature; config values are optional
        self.email_address = email_address
        self.app_password = app_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port

        # Records of activity for assertions in tests
        self.sent_messages: List[Dict[str, Any]] = []
        # Simulated unread messages returned by check_unread
        self._unread_messages: List[Dict[str, Any]] = []

        # Optional mapping of UID -> raw message metadata to simulate reply-by-uid
        # Each value should be a dict containing keys similar to parsed email headers:
        # {"Message-ID": "<...>", "Reply-To": "x@y.com", "From": "x@y.com", "References": "..."}
        self.messages_by_uid: Dict[int, Dict[str, Any]] = {}

        # Track which UIDs were marked seen via check_unread(mark_seen=True)
        self.marked_seen_uids: List[int] = []

    # Helpers for tests
    def add_unread(self, msg: Dict[str, Any]) -> None:
        """Add a synthetic unread message that will be returned by check_unread.

        Expected keys: 'id' (str), 'uid' (int), 'from', 'subject', 'date', 'body', 'clean_body'
        """
        self._unread_messages.append(msg.copy())
        # Also populate messages_by_uid for convenience if uid present
        uid = msg.get("uid")
        if uid:
            self.messages_by_uid[int(uid)] = {
                "Message-ID": msg.get("message_id") or f"<mock-{uid}@local>",
                "Reply-To": msg.get("from"),
                "From": msg.get("from"),
                "References": msg.get("references", ""),
            }

    def clear_unread(self) -> None:
        self._unread_messages.clear()
        self.messages_by_uid.clear()
        self.marked_seen_uids.clear()

    # Public API mirroring the real handler
    def send_email(
        self,
        to_address: Optional[str],
        subject: str,
        body: str,
        thread_id: Optional[int] = None,
        reply_uid: Optional[int] = None,
    ) -> bool:
        """Record a send_email call and optionally simulate reply-by-uid behavior.

        The function returns True to mirror the real handler. It raises ValueError
        for invalid to_address similar to the real EmailHandler.
        """
        # Basic validation mirroring real EmailHandler behaviour
        if to_address is not None and (not isinstance(to_address, str) or not to_address):
            raise ValueError("to_address must be a non-empty string or None when reply_uid is used")

        record: Dict[str, Any] = {
            "to_address": to_address,
            "subject": subject,
            "body": body,
            "thread_id": thread_id,
            "reply_uid": reply_uid,
            "in_reply_to": None,
            "references": None,
        }

        # If reply_uid provided, use messages_by_uid to fill headers and default recipient
        if reply_uid is not None:
            meta = self.messages_by_uid.get(int(reply_uid))
            if meta:
                # set default recipient if not provided
                if not to_address and meta.get("Reply-To"):
                    record["to_address"] = meta.get("Reply-To")
                record["in_reply_to"] = meta.get("Message-ID")
                record["references"] = meta.get("References") or meta.get("Message-ID")

        # If thread_id provided, simulate synthetic message-id in references when none present
        if thread_id is not None and record["in_reply_to"] is None and record["references"] is None:
            domain = "local"
            if isinstance(self.email_address, str) and "@" in self.email_address:
                domain = self.email_address.split("@", 1)[1]
            record["in_reply_to"] = f"<thread-{int(thread_id)}@{domain}>"
            record["references"] = record["in_reply_to"]

        self.sent_messages.append(record)
        return True

    def check_unread(self, mark_seen: bool = False) -> List[Dict[str, Any]]:
        """Return the configured unread messages.

        If mark_seen is True, messages with a numeric 'uid' are recorded in
        `marked_seen_uids` and removed from the unread list to simulate server-side
        marking. The returned list is a shallow copy so tests can mutate it safely.
        """
        results = [m.copy() for m in self._unread_messages]
        if mark_seen:
            remaining = []
            for m in self._unread_messages:
                uid = m.get("uid")
                if isinstance(uid, int):
                    self.marked_seen_uids.append(uid)
                else:
                    remaining.append(m)
            # Remove messages that had numeric UIDs
            self._unread_messages = remaining
        return results


__all__ = ["MockEmailHandler"]
