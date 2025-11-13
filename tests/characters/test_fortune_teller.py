"""Fortune Teller tests.

Includes tests for reveal behaviour and red-herring handling.
"""
from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def test_ft_no_state_change():
    players = make_players()

    # Fortune Teller (5) investigates players 2 and 4 (two-player investigate)
    ft_action = Message(priority=4, resolved=True, response=[2, 4], playernumber=5)

    res = perform_night_actions(players, [ft_action])

    # No player state that affects game (dead/poisoned/protected) should change
    for p in res:
        assert p["dead"] is False
        assert p["poisoned"] is False
        assert p["protected"] is False

    # Fortune Teller should receive an informational reveal stored on their player state
    ft = next(p for p in res if p["id"] == 5)
    assert ft.get("info_for_player") == "neither is evil"


def test_ft_detects_imp():
    players = make_players()

    # Fortune Teller (5) investigates players 1 (Imp) and 4
    ft_action = Message(priority=4, resolved=True, response=[1, 4], playernumber=5)

    res = perform_night_actions(players, [ft_action])

    ft = next(p for p in res if p["id"] == 5)
    assert ft.get("info_for_player") == "at least one is evil"


def test_ft_red_herring_counts():
    players = make_players()

    # Configure the Fortune Teller's red herring to be player 4
    ft = next(p for p in players if p["role"] == "Fortune Teller")
    ft["red_herring"] = 4

    # Fortune Teller (5) investigates players 2 and 4 (both non-Imp, but 4 is red herring)
    ft_action = Message(priority=4, resolved=True, response=[2, 4], playernumber=5)

    res = perform_night_actions(players, [ft_action])

    ft_after = next(p for p in res if p["id"] == 5)
    assert ft_after.get("info_for_player") == "at least one is evil"
