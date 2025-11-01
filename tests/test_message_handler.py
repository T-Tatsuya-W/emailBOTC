"""Unit tests for utils.message_handler.MessageHandler

This test constructs MessageHandler with the mock email handler and asserts
the example message list is present and has the expected fields.
"""
import unittest

from utils.message_handler import MessageHandler
from utils.mock_email_handler import MockEmailHandler


class TestMessageHandler(unittest.TestCase):
    def test_constructor_initializes_example_messages(self):
        mock = MockEmailHandler(email_address="me@example.com")
        handler = MessageHandler(email_handler=mock)

        # basic assertions about the example messages
        self.assertIsInstance(handler.messages, list)
        self.assertGreaterEqual(len(handler.messages), 1)

        first = handler.messages[0]
        self.assertEqual(first.priority, 1)
        self.assertFalse(first.resolved)
        self.assertIsInstance(first.response, list)
        # response has up to two integers in our example
        self.assertEqual(first.response, [1, 2])
        self.assertEqual(first.address, "player1@example.com")
        self.assertEqual(first.subject, "Welcome")
        self.assertEqual(first.playernumber, 1)
        # expected_response_number should be an int in {0,1,2}
        self.assertIsInstance(first.expected_response_number, int)
        self.assertIn(first.expected_response_number, (0, 1, 2))
        self.assertEqual(first.expected_response_number, 2)

    def test_get_unresolved_returns_unresolved_messages(self):
        handler = MessageHandler()
        # mark second message resolved and verify filtering
        if len(handler.messages) > 1:
            handler.messages[1].resolved = True
        unresolved = handler.get_unresolved()
        for m in unresolved:
            self.assertFalse(m.resolved)

    def test_has_message_matches_subject_and_address(self):
        handler = MessageHandler()
        # existing example message (first) should be found
        self.assertTrue(handler.has_message("Welcome", "player1@example.com"))
        # case-insensitive match
        self.assertTrue(handler.has_message("welcome", "PLAYER1@EXAMPLE.COM"))
        # non-existing combinations should return False
        self.assertFalse(handler.has_message("Nope", "noone@example.com"))

    def test_parse_response_integers_various_formats(self):
        handler = MessageHandler()

        cases = {
            "3,6.": [3, 6],
            "3": [3],
            "  12/34 some text": [12, 34],
            "no numbers here": [],
            "7 8 extra": [7, 8],
            "9-10": [9, 10],
            "": [],
            None: [],
            "I want to nominate 5 and 11.": [5, 11],
        }

        for inp, expected in cases.items():
            res = handler.parse_response_integers(inp)
            self.assertEqual(res, expected, msg=f"input={inp!r}")

    def test_process_incoming_marks_resolved_when_expected_count_matches(self):
        mock = MockEmailHandler()
        handler = MessageHandler(email_handler=mock)

        # create an incoming unread message that matches the first example
        mock.add_unread({
            "id": "10",
            "uid": 500,
            "from": "player1@example.com",
            "subject": "Welcome",
            "date": "now",
            "body": "3,6.",
            "clean_body": "3,6.",
        })

        unread = mock.check_unread()
        processed = handler.process_incoming(unread)
        self.assertEqual(processed, 1)
        # first message should now be resolved
        self.assertTrue(handler.messages[0].resolved)
        self.assertEqual(handler.messages[0].response, [3, 6])

    def test_process_incoming_ignores_when_count_mismatch(self):
        mock = MockEmailHandler()
        handler = MessageHandler(email_handler=mock)

        # create incoming message with only one number but message expects 2
        mock.add_unread({
            "id": "11",
            "uid": 501,
            "from": "player1@example.com",
            "subject": "Welcome",
            "date": "now",
            "body": "3",
            "clean_body": "3",
        })

        unread = mock.check_unread()
        processed = handler.process_incoming(unread)
        self.assertEqual(processed, 0)
        self.assertFalse(handler.messages[0].resolved)


if __name__ == "__main__":
    unittest.main()
