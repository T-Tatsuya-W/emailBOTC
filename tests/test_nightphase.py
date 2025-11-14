"""Tests for the `nightphase` function in `main.py`.

This file provides a template test that injects a mock `EmailHandler` which
automatically enqueues reply messages (so replies can be defined at the email
handler level). The test demonstrates verifying player state changes after
the night phase (for example, that an Imp's kill is applied).
"""
from typing import List

import pytest

from utils.message_handler import Message
from utils.email_handler import EmailHandler
from main import nightphase


class AutoReplyEmailHandler:
    """A mock email handler that records sends and enqueues replies.

    Usage: provide a `responses` mapping from recipient email to the reply
    body you want the mock to produce when a message is sent to that address.
    The mock will append a reply with the exact subject it was sent (the
    MessageHandler appends the internal " [ID: ...]" suffix before calling
    `send_email`, so that subject is used for matching).
    """

    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.sent = []
        self._inbox: List[dict] = []

    def send_email(self, to_address, subject, body, thread_id=None, reply_uid=None):
        # record the outgoing message
        self.sent.append({"to": to_address, "subject": subject, "body": body})

        # enqueue a reply if we have a configured response for this recipient
        resp = self.responses.get(to_address)
        if resp is not None:
            self._inbox.append({
                "id": "1",
                "uid": 1,
                "from": to_address,
                "subject": subject,
                "clean_body": resp,
            })

        return True

    def check_unread(self, mark_seen: bool = False):
        out = list(self._inbox)
        # emulate consuming the inbox
        self._inbox.clear()
        return out

    def extract_ints_from_body(self, body: str):
        return EmailHandler().extract_ints_from_body(body)


def make_players(imp_target_email: str = "target@example.com"):
    """Return a minimal 2-player game state where player 1 is an Imp."""
    default_email = imp_target_email
    return [
        {
            "id": 1,
            "email": "imp@example.com",
            "name": "impPlayer",
            "alignment": "Evil",
            "role": "Imp",
            "drunk": False,
            "poisoned": False,
            "dead": False,
            "canVote": True,
            "protected": False,
            "nightResponse": 1,
            "canChooseSelf": False,
            "nightActionPriority": 3,
        },
        {
            "id": 2,
            "email": default_email,
            "name": "targetPlayer",
            "alignment": "Good",
            "role": "Villager",
            "drunk": False,
            "poisoned": False,
            "dead": False,
            "canVote": True,
            "protected": False,
            "nightResponse": 0,
            "canChooseSelf": False,
            "nightActionPriority": 4,
        },
    ]


def test_imp_kills_via_email():
    """imp kills target via email replies"""

    players = make_players(imp_target_email="target@example.com")

    target_player = next(p for p in players if  p["role"] == "Villager")

    # Configure auto-replies: when the Imp's prompt is sent to imp@example.com
    # it should reply with the integer '2' to target player id 2, but since the
    # Imp is the sender, we want the Imp's email to reply with the chosen id.
    # The MessageHandler sends prompts to each player's own email address; the
    # player replies come "from" that same address. Therefore we set the
    # response for the Imp's email to be '2' (the target id).
    responses = {
        "imp@example.com": str(target_player["id"]),
        # target has no action but we could also define one
        "target@example.com": "",
    }

    mock_eh = AutoReplyEmailHandler(responses=responses)

    # Run nightphase using the injected mock email handler. nightphase will
    # construct its own MessageHandler wired to this email handler, and the
    # mock will enqueue the replies as soon as `send_email` is called.
    result_players = nightphase(players, email_handler=mock_eh)

    # Find target player and assert they were killed by the Imp
    target = next(p for p in result_players if p["role"] == "Villager")
    assert target["dead"] is True

    # Basic sanity: ensure the mock recorded outgoing emails
    assert any(s["to"] == "imp@example.com" for s in mock_eh.sent)
