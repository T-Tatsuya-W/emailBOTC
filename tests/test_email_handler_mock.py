"""unittest tests for utils.mock_email_handler.MockEmailHandler

Converted from pytest to unittest so the test suite can run without external
dependencies.
"""
import unittest

from utils.mock_email_handler import MockEmailHandler


class TestMockEmailHandler(unittest.TestCase):
    def test_send_email_records_call(self):
        mock = MockEmailHandler(email_address="me@example.com")
        res = mock.send_email("you@example.com", "Hello", "Body text")
        self.assertTrue(res)
        self.assertEqual(len(mock.sent_messages), 1)
        rec = mock.sent_messages[0]
        self.assertEqual(rec["to_address"], "you@example.com")
        self.assertEqual(rec["subject"], "Hello")
        self.assertEqual(rec["body"], "Body text")

    def test_send_email_reply_uid_sets_recipient_and_headers(self):
        mock = MockEmailHandler(email_address="me@example.com")
        # add an unread message which will populate messages_by_uid
        mock.add_unread({
            "id": "1",
            "uid": 42,
            "from": "orig@example.com",
            "subject": "Orig",
            "date": "now",
            "body": "Hi",
            "clean_body": "Hi",
            "message_id": "<orig-42@local>",
        })

        # reply without specifying to_address should use Reply-To/From from the original
        res = mock.send_email(None, "Re: Orig", "Reply body", reply_uid=42)
        self.assertTrue(res)
        self.assertEqual(len(mock.sent_messages), 1)
        rec = mock.sent_messages[0]
        self.assertEqual(rec["to_address"], "orig@example.com")
        self.assertEqual(rec["in_reply_to"], "<orig-42@local>")
        self.assertIsNotNone(rec.get("references"))

    def test_check_unread_and_mark_seen(self):
        mock = MockEmailHandler()
        mock.add_unread({
            "id": "1",
            "uid": 100,
            "from": "a@b.com",
            "subject": "S",
            "date": "d",
            "body": "B",
            "clean_body": "B",
        })
        mock.add_unread({
            "id": "2",
            "uid": None,
            "from": "c@d.com",
            "subject": "S2",
            "date": "d2",
            "body": "B2",
            "clean_body": "B2",
        })

        # Without marking seen, both messages are returned and remain in the mock
        res = mock.check_unread(mark_seen=False)
        self.assertEqual(len(res), 2)
        self.assertEqual(len(mock._unread_messages), 2)

        # With mark_seen=True, messages that have numeric UIDs are recorded and removed
        res2 = mock.check_unread(mark_seen=True)
        self.assertEqual(len(res2), 2)
        self.assertIn(100, mock.marked_seen_uids)
        # After marking seen, only the message without numeric UID remains
        remaining = mock.check_unread(mark_seen=False)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], "2")


if __name__ == "__main__":
    unittest.main()
