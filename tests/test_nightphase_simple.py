"""Simple, minimal tests for `nightphase` that bypass email entirely.

This file provides a very small template you can copy and extend: define the
`players` list you want to test and a `responses` mapping that maps player
numbers (or emails) to the reply you want them to send. The `SimpleMessageHandler`
will apply the responses immediately so the night phase can be exercised
deterministically.
"""
from utils.test_helpers import SimpleMessageHandler

from main import nightphase


def make_players():
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
            "email": "target@example.com",
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


def test_imp_kills_target_with_simple_handler():
    """Run a night where player 1 (Imp) chooses player 2.

    This demonstrates passing a full players list and a responses mapping and
    asserting the resulting players list is updated as expected.
    """

    players = make_players()

    # Configure responses: player 1 chooses target id 2. Keys may be ints
    # (player number) or the player's email address.
    responses = {1: "2"}

    handler = SimpleMessageHandler(responses=responses)

    result = nightphase(players, message_handler=handler)

    target = next(p for p in result if p["id"] == 2)
    assert target["dead"] is True
