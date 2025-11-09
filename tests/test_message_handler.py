"""Unit tests for MessageHandler using a mocked EmailHandler.

These tests exercise the current API in `utils.message_handler` and avoid
network I/O by providing a mock `email_handler` with `send_email` and
`check_unread` behaviour simulated.
"""
import unittest
import itertools
from unittest.mock import Mock, create_autospec
from typing import List

from utils.message_handler import MessageHandler, Message, addresses_match, normalize_subject
from utils.email_handler import EmailHandler


class SimpleTests(unittest.TestCase):
    def test_extract_ints_from_email_handler(self):
        # EmailHandler provides a pure helper to extract ints from text
        eh = EmailHandler()
        self.assertEqual(eh.extract_ints_from_body("3,6."), [3, 6])
        self.assertEqual(eh.extract_ints_from_body("no numbers"), [])

    def test_addresses_and_subject_helpers(self):
        self.assertTrue(addresses_match("alice@example.com", "Alice <alice@example.com>"))
        self.assertFalse(addresses_match("bob@example.com", "alice@example.com"))
        self.assertEqual(normalize_subject("Re: Re: Hello"), "hello")
        self.assertEqual(normalize_subject("FW: Test"), "test")

    def test_send_prompts_uses_email_handler(self):
        mock_eh = Mock()
        mock_eh.send_email.return_value = True
        mock_eh.check_unread.return_value = []

        msgs = [Message(priority=1, address="p@example.com", subject="S")]
        mh = MessageHandler(email_handler=mock_eh, messages=list(msgs), max_player_id=10)

        returned = mh.send_and_resolve_all(msgs, poll_every=0.01, poll_for=0.02)
        # send_email should have been called once per message
        mock_eh.send_email.assert_called()
        self.assertEqual(len(returned), 1)

    def test_monitor_until_resolved_with_mock_side_effects(self):
        # Use create_autospec to ensure the mock matches EmailHandler's API
        mock_eh = create_autospec(EmailHandler, instance=True)

        messages = [
            Message(priority=1, address="p1@example.com", subject="A", expected_response_number=2, playernumber=1),
            Message(priority=2, address="p2@example.com", subject="B", expected_response_number=1, playernumber=2),
        ]

        # Simulate first poll returning reply for player 1, second poll for player 2
        first = [{"id": "1", "uid": 1, "from": "p1@example.com", "subject": messages[0].subject + f" [ID: {id(messages[0])}]", "clean_body": "3,6"}]
        second = [{"id": "2", "uid": 2, "from": "p2@example.com", "subject": messages[1].subject + f" [ID: {id(messages[1])}]", "clean_body": "7"}]
        mock_eh.check_unread.side_effect = itertools.chain([first, second], itertools.repeat([]))
        mock_eh.send_email.return_value = True
        # Use the real extraction helper so the mock can parse ints from bodies
        mock_eh.extract_ints_from_body = EmailHandler().extract_ints_from_body

        mh = MessageHandler(email_handler=mock_eh, messages=list(messages), max_player_id=10)
        result = mh.send_and_resolve_all(messages, poll_every=0.01, poll_for=0.2)

        resolved_count = len([m for m in result if m.resolved])
        self.assertEqual(resolved_count, 2)


if __name__ == "__main__":
    unittest.main()
