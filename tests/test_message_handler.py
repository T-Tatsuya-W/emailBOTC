"""pytest-style tests for MessageHandler using a simple mock EmailHandler.

This file contains fixtures and a small MockEmailHandler implementation so
you can extend tests easily without any network I/O. It demonstrates the
basic happy-path and helper tests used by the message handler.
"""
from typing import List

import pytest

from utils.message_handler import MessageHandler, Message, addresses_match, normalize_subject
from utils.email_handler import EmailHandler


class MockEmailHandler:
    """A tiny in-file mock used by tests.

    - send_email records sends to `self.sent` and returns True
    - check_unread returns the current `_inbox` list and clears it
    - extract_ints_from_body delegates to the real EmailHandler helper
    """

    def __init__(self):
        self.sent = []
        self._inbox: List[dict] = []

    def send_email(self, to_address, subject, body, thread_id=None, reply_uid=None):
        self.sent.append({"to": to_address, "subject": subject, "body": body})
        return True

    def check_unread(self, mark_seen: bool = False):
        out = list(self._inbox)
        # emulate consuming the messages
        self._inbox.clear()
        return out

    def extract_ints_from_body(self, body: str):
        return EmailHandler().extract_ints_from_body(body)


@pytest.fixture
def mock_eh():
    return MockEmailHandler()


@pytest.fixture
def sample_messages() -> List[Message]:
    m1 = Message(
        priority=1,
        address="p1@example.com",
        subject="Night Phase Actions",
        body="Choose a player (send 1 integer)",
        playernumber=1,
        expected_response_number=1,
        playerName="P1",
        canChooseSelf=False,
    )
    m2 = Message(
        priority=2,
        address="p2@example.com",
        subject="Night Phase Actions",
        body="Choose a player (send 1 integer)",
        playernumber=2,
        expected_response_number=1,
        playerName="P2",
        canChooseSelf=False,
    )
    return [m1, m2]


def test_extract_ints_from_email_handler():
    eh = EmailHandler()
    assert eh.extract_ints_from_body("3,6.") == [3, 6]
    assert eh.extract_ints_from_body("no numbers") == []


def test_addresses_and_subject_helpers():
    assert addresses_match("alice@example.com", "Alice <alice@example.com>")
    assert not addresses_match("bob@example.com", "alice@example.com")
    assert normalize_subject("Re: Re: Hello") == "hello"
    assert normalize_subject("FW: Test") == "test"


def test_send_prompts_uses_email_handler(mock_eh, sample_messages):
    mh = MessageHandler(email_handler=mock_eh, messages=list(sample_messages), max_player_id=10)
    returned = mh.send_and_resolve_all(list(sample_messages), poll_every=0.01, poll_for=0.02)
    # each message should have triggered a send
    assert len(mock_eh.sent) == len(sample_messages)
    assert isinstance(returned, list)


def test_send_and_resolve_all_happy_path(mock_eh, sample_messages):
    # Construct handler and perform the initial send so subjects are augmented
    mh = MessageHandler(email_handler=mock_eh, messages=list(sample_messages), max_player_id=10)
    # initial send to populate subjects with IDs
    mh.send_and_resolve_all(sample_messages, poll_every=0.01, poll_for=0.01)

    # Now push matching replies into the mock inbox. The MessageHandler appends
    # " [ID: <id>]" to subjects when sending — tests can mirror that exact
    # string to match the message by subject.
    mock_eh._inbox.append(
        {
            "id": "1",
            "uid": 1,
            "from": "p1@example.com",
            "subject": sample_messages[0].subject + f" [ID: {id(sample_messages[0])}]",
            "clean_body": "2",
        }
    )
    mock_eh._inbox.append(
        {
            "id": "2",
            "uid": 2,
            "from": "p2@example.com",
            "subject": sample_messages[1].subject + f" [ID: {id(sample_messages[1])}]",
            "clean_body": "1",
        }
    )

    # Run the resolver loop again to process the inbox entries
    res = mh.send_and_resolve_all(sample_messages, poll_every=0.01, poll_for=0.2)
    assert all(m.resolved for m in res)

