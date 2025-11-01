"""Message handling utilities.

Defines a simple Message dataclass and a MessageHandler which will orchestrate
operations involving an EmailHandler (real or mock). For now the handler only
stores an example message list to be used by unit tests while we build
functionality incrementally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Message:
    """Represents a message to be handled.

    Fields required by the user request:
    - priority: int (1,2,3)
    - resolved: bool
    - response: list of up to 2 integers (not enforced here)
    - address: str
    - subject: str
    - body: str
    - playernumber: int
    - responseBody: str
    """

    priority: int
    resolved: bool = False
    response: List[int] = field(default_factory=list)
    address: str = ""
    subject: str = ""
    body: str = ""
    playernumber: int = 0
    responseBody: str = ""
    # number of expected integer responses (0, 1 or 2)
    expected_response_number: int = 0


class MessageHandler:
    """Handles a list of Message objects and delegates email operations.

    The handler accepts an `email_handler` argument to allow swapping the
    real `EmailHandler` for `MockEmailHandler` in tests.
    """

    def __init__(self, email_handler: Optional[object] = None) -> None:
        # store the provided email handler (real or mock) for future use
        self.email_handler = email_handler

        # Example messages list matching the specified schema. Tests may
        # construct the handler and assert these example items exist.
        self.messages: List[Message] = [
            Message(
                priority=1,
                resolved=False,
                response=[1, 2],
                address="player1@example.com",
                subject="Welcome",
                body="Hello player 1, this is a test message.",
                playernumber=1,
                responseBody="",
                expected_response_number=2,
            ),
            Message(
                priority=2,
                resolved=False,
                response=[],
                address="player2@example.com",
                subject="Follow up",
                body="Second example message body.",
                playernumber=2,
                responseBody="",
                expected_response_number=0,
            ),
        ]

    def get_unresolved(self) -> List[Message]:
        """Return the list of messages that are not resolved yet."""
        return [m for m in self.messages if not m.resolved]

    def has_message(self, subject: str, address: str) -> bool:
        """Return True if a message with matching subject and address exists.

        Matching is performed by trimming whitespace and comparing case-insensitively.

        Args:
            subject: subject to match against messages' subject
            address: email address to match against messages' address

        Returns:
            True if a corresponding message exists, False otherwise.
        """
        if subject is None or address is None:
            return False

        subj = subject.strip().casefold()
        addr = address.strip().casefold()

        for m in self.messages:
            m_subj = (m.subject or "").strip().casefold()
            m_addr = (m.address or "").strip().casefold()
            if m_subj == subj and m_addr == addr:
                return True
        return False

    def _find_message(self, subject: str, address: str) -> Optional[Message]:
        """Return the first message matching subject and address, or None.

        Matching uses the same normalization as `has_message` but is a bit more
        tolerant for typical email 'From' headers (e.g. "Name <addr>"). If the
        handler contains multiple matches, the first is returned.
        """
        if subject is None or address is None:
            return None

        subj = subject.strip().casefold()
        addr = address.strip().casefold()

        for m in self.messages:
            m_subj = (m.subject or "").strip().casefold()
            m_addr = (m.address or "").strip().casefold()
            # tolerate cases where the incoming 'from' contains a display name
            if m_subj == subj and (m_addr == addr or m_addr in addr or addr in m_addr):
                return m
        return None

    def process_incoming(self, incoming_msgs: List[dict]) -> int:
        """Process incoming messages, matching them to known messages.

        For each incoming message (dict expected to contain at least 'subject',
        'from' and 'body' or 'clean_body'), find the corresponding Message in
        `self.messages`. If found, extract integers from the incoming body and
        if the number of integers equals the message's
        `expected_response_number`, mark the Message as resolved and store the
        parsed integers and response body.

        Returns the number of messages that were marked resolved during this
        invocation.
        """
        resolved_count = 0
        for inc in incoming_msgs:
            subj = inc.get("subject") or inc.get("Subject") or ""
            frm = inc.get("from") or inc.get("From") or ""
            body = inc.get("clean_body") or inc.get("body") or inc.get("Body") or ""

            m = self._find_message(subj, frm)
            if m is None:
                continue

            # skip already resolved messages
            if m.resolved:
                continue

            parsed = self.parse_response_integers(body)
            if len(parsed) == getattr(m, "expected_response_number", 0):
                m.resolved = True
                m.response = parsed
                m.responseBody = body
                resolved_count += 1

        return resolved_count

    def parse_response_integers(self, text: Optional[str]) -> List[int]:
        """Extract up to two integers from the start of `text`.

        The function attempts to find one or two integers appearing at the
        beginning of `text`, possibly separated by non-digit characters such
        as commas, slashes, spaces, hyphens, semicolons etc. Examples:

        - "3,6." -> [3, 6]
        - "3" -> [3]
        - "12/34 some text" -> [12, 34]
        - "no numbers" -> []

        Returns a list of 0, 1 or 2 integers.
        """
        import re

        if not text:
            return []

        # Find all integer substrings anywhere in the text and return the
        # first up to two values. This handles inputs like "I want 5 and 11"
        # as well as leading formats like "3,6.".
        nums = re.findall(r"[0-9]+", text)
        results: List[int] = []
        for n in nums[:2]:
            try:
                results.append(int(n))
            except Exception:
                # ignore parse failures (shouldn't happen for \d+)
                continue
        return results


__all__ = ["Message", "MessageHandler"]
