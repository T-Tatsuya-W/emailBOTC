"""Integration tests for GameController round lifecycle (send -> collect -> execute)."""
from game.controller import GameController
from utils.message_handler import MessageHandler


def test_full_round_collects_and_executes_actions():
    mh = MessageHandler()

    players = [
        {"playername": "P1", "player_email": "p1@example.com", "player_id": "p1", "expected_ints": 1},
        {"playername": "P2", "player_email": "p2@example.com", "player_id": "p2", "expected_ints": 1},
    ]

    gc = GameController(players, mh)
    batch_id = gc.start_round(prompt_text="Provide one number", required_ints=1)

    # collect the unresolved messages for the batch
    msgs = [m for m in mh.get_unresolved() if m.batch_id == batch_id]
    assert len(msgs) == 2

    # resolve both messages (in any order) - match by player_id to be explicit
    msgs_by_player = {m.player_id: m for m in msgs}
    assert mh.resolve(msgs_by_player["p2"].id, "7") is True
    assert mh.resolve(msgs_by_player["p1"].id, "3") is True

    # GameController should have executed actions and set last_numbers on players
    p1 = gc.registry.get("p1")
    p2 = gc.registry.get("p2")
    assert getattr(p1, "last_numbers") == [3]
    assert getattr(p2, "last_numbers") == [7]
    # last_actions recorded
    assert len(gc.last_actions) == 2
