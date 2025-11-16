from utils.dayphase import (
    get_day_nominations_first,
    select_nomination_from_messages,
)
from utils.message_handler import MessageHandler, Message
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


def make_sample_players():
    return [
        {"id": 1, "name": "P1", "email": "p1@example.com", "dead": False},
        {"id": 2, "name": "P2", "email": "p2@example.com", "dead": False},
        {"id": 3, "name": "P3", "email": "p3@example.com", "dead": True},
        {"id": 4, "name": "P4", "email": "p4@example.com", "dead": True, "canVote": False},
    ]


def test_nomination_selection():
    mock = MockEmailHandler()
    players = make_sample_players()

    messages = get_day_nominations_first(players)
    mh = MessageHandler(email_handler=mock, messages=list(messages), max_player_id=len(players))
    # initial send (attach subject IDs)
    mh.send_and_resolve_all(messages, poll_every=0.01, poll_for=0.01)

    # Simulate player 1 nominating player 2
    mock._inbox.append(
        {
            "id": "1",
            "uid": 1,
            "from": messages[0].address,
            "subject": messages[0].subject,
            "clean_body": "2",
        }
    )

    mh.send_and_resolve_all(messages, poll_every=0.01, poll_for=0.2)

    nomination = select_nomination_from_messages(messages, players)
    assert nomination == 2


def test_voting_and_ghost_vote():
    # Use a responding mock that generates replies for the sent messages
    class MockRespondingEmailHandler(MockEmailHandler):
        def __init__(self, planned_votes):
            super().__init__()
            self.planned_votes = planned_votes
            self._generated = False

        def check_unread(self, mark_seen: bool = False):
            # Generate responses only once based on what was sent
            if self._generated:
                out = list(self._inbox)
                self._inbox.clear()
                return out

            responses = []
            # self.sent contains the send_email calls with final subject
            for i, sent in enumerate(self.sent):
                to = sent.get("to")
                subj = sent.get("subject")
                vote = self.planned_votes.get(to)
                if vote is not None:
                    responses.append({
                        "id": str(i + 1),
                        "uid": i + 1,
                        "from": to,
                        "subject": subj,
                        "clean_body": vote,
                    })

            self._generated = True
            return responses

    players = make_sample_players()
    # Planned votes: P1 YES, P2 NO, P3 YES (dead allowed once), P4 no vote
    planned = {
        "p1@example.com": "YES",
        "p2@example.com": "NO",
        "p3@example.com": "YES",
    }

    mock = MockRespondingEmailHandler(planned_votes=planned)

    # Call the production helper which both sends and collects votes
    votes = []
    # We call get_day_voting by importing it from dayphase to exercise
    from utils.dayphase import get_day_voting

    vote_results = get_day_voting(players, nominated_id=2, message_handler=None, email_handler=mock, poll_every=0.01, poll_for=0.2)

    # vote_results is a list of responseBody strings aligned with players
    assert vote_results[0].casefold().strip().startswith("yes")
    assert vote_results[1].casefold().strip().startswith("no")
    assert vote_results[2].casefold().strip().startswith("yes")
    # Dead player 3 should have lost their ghost vote
    assert players[2].get("canVote") is False
    # Player 4 had canvote False and should not have been asked; their entry is empty
    assert vote_results[3] == ""
