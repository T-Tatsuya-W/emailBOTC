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


def test_imp_kills_with_simple_handler():
    """imp kills target with simple handler"""

    players = make_players()

    imp = next(p for p in players if p["role"] == "Imp")
    target_player = next(p for p in players if p["role"] == "Villager")

    # Configure responses: Imp chooses the villager. Keys may be ints
    # (player number) or the player's email address.
    responses = {imp["id"]: str(target_player["id"])}

    handler = SimpleMessageHandler(responses=responses)

    result = nightphase(players, message_handler=handler)

    target = next(p for p in result if p["role"] == "Villager")
    assert target["dead"] is True
