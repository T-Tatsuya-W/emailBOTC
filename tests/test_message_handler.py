"""Simplified unit tests demonstrating unittest and unittest.mock.

These tests focus on core `MessageHandler` behaviour and use `unittest.mock`
to provide a lightweight email handler substitute without an external mock
class file.
"""
import unittest
from unittest.mock import Mock, create_autospec
from typing import List

from utils.message_handler import MessageHandler, Message
from utils.email_handler import EmailHandler


class SimpleTests(unittest.TestCase):
    def test_parse_response_integers(self):
        mh = MessageHandler()
        self.assertEqual(mh.parse_response_integers("3,6."), [3, 6])
        self.assertEqual(mh.parse_response_integers("no numbers"), [])

    def test_has_message(self):
        msgs: List[Message] = [
            Message(priority=1, address="a@b.com", subject="Hi"),
        ]
        mh = MessageHandler(messages=msgs)
        self.assertTrue(mh.has_message("Hi", "a@b.com"))
        self.assertFalse(mh.has_message("Other", "a@b.com"))

    def test_send_night_emails_uses_email_handler(self):
        mock_eh = Mock()
        mock_eh.send_email.return_value = True

        msgs = [Message(priority=1, address="p@example.com", subject="S")]
        mh = MessageHandler(email_handler=mock_eh, messages=msgs)

        sent = mh.send_night_emails("subj", "body")
        self.assertEqual(sent, 1)
        mock_eh.send_email.assert_called_once()

    def test_monitor_until_resolved_with_mock_side_effects(self):
        # Use create_autospec to ensure the mock matches EmailHandler's API
        mock_eh = create_autospec(EmailHandler, instance=True)

        messages = [
            Message(priority=1, address="p1@example.com", subject="A", expected_response_number=2),
            Message(priority=2, address="p2@example.com", subject="B", expected_response_number=1),
        ]

        # First poll returns one message, second poll returns the other
        first = [{"id": "1", "uid": 1, "from": "p1@example.com", "subject": "A", "clean_body": "3,6"}]
        second = [{"id": "2", "uid": 2, "from": "p2@example.com", "subject": "B", "clean_body": "7"}]
        mock_eh.check_unread.side_effect = [first, second, []]

        mh = MessageHandler(email_handler=mock_eh, messages=messages)
        resolved = mh.monitor_until_resolved(poll_interval=0.01, max_polls=10, mark_seen=False)
        self.assertEqual(resolved, 2)


if __name__ == "__main__":
    unittest.main()
