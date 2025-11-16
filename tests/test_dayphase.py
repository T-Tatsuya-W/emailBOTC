from utils.dayphase import dayphase, get_day_messages, select_nomination_from_messages
from utils.message_handler import MessageHandler
from utils.email_handler import EmailHandler


class MockEmailHandler:
    def __init__(self):
        self.sent = []
        self._inbox = []

    def send_email(self, to_address, subject, body, thread_id=None, reply_uid=None):
        self.sent.append({"to": to_address, "subject": subject, "body": body})
        return True

    def check_unread(self, mark_seen: bool = False):
        out = list(self._inbox)
        self._inbox.clear()
        return out

    def extract_ints_from_body(self, body: str):
        return EmailHandler().extract_ints_from_body(body)


def make_sample_players(n=5):
    return [
        {
            "id": i + 1,
            "name": f"P{i+1}",
            "email": f"p{i+1}@example.com",
            "dead": False,
            "role": "Villager",
        }
        for i in range(n)
    ]


def test_dayphase_returns_players_list():
    mock_eh = MockEmailHandler()
    players = make_sample_players(6)
    out = dayphase(players, email_handler=mock_eh, poll_every=0.01, poll_for=0.01)
    assert isinstance(out, list)
    assert len(out) == len(players)
    assert {p["id"] for p in out} == {p["id"] for p in players}


def test_dayphase_no_nomination():
    mock_eh = MockEmailHandler()
    players = make_sample_players(5)
    messages = get_day_messages(players)

    mh = MessageHandler(email_handler=mock_eh, messages=list(messages), max_player_id=len(players))
    # Initial send to attach subject IDs
    mh.send_and_resolve_all(messages, poll_every=0.01, poll_for=0.01)
    # No replies added to mock inbox -> process; messages will be marked resolved
    mh.send_and_resolve_all(messages, poll_every=0.01, poll_for=0.02)

    nomination = select_nomination_from_messages(messages, players)
    assert nomination is None


def test_dayphase_with_nomination():
    mock_eh = MockEmailHandler()
    players = make_sample_players(6)
    messages = get_day_messages(players)

    mh = MessageHandler(email_handler=mock_eh, messages=list(messages), max_player_id=len(players))
    # initial send so subjects get augmented with [ID: ...]
    mh.send_and_resolve_all(messages, poll_every=0.01, poll_for=0.01)

    # Simulate a player replying with a nomination for player 3
    mock_eh._inbox.append(
        {
            "id": "1",
            "uid": 1,
            "from": messages[0].address,
            "subject": messages[0].subject + f" [ID: {id(messages[0])}]",
            "clean_body": "3",
        }
    )

    # Process the inbox and accept the response
    mh.send_and_resolve_all(messages, poll_every=0.01, poll_for=0.2)

    nomination = select_nomination_from_messages(messages, players)
    assert nomination == 3
