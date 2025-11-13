"""Poisoner-related tests.

Tests that are primarily about poisoning and related interactions.
"""
from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def test_poisoner_marks_poisoned():
    players = make_players()

    # Poisoner (2) poisons player 4
    poison_action = Message(priority=1, resolved=True, response=[4], playernumber=2)

    res = perform_night_actions(players, [poison_action])

    target = next(p for p in res if p["id"] == 4)
    assert target["poisoned"] is True
    assert target["dead"] is False


def test_monk_poisoned_cannot_protect():
    players = make_players()

    # Poisoner (2) poisons the Monk (3)
    poison_action = Message(priority=1, resolved=True, response=[3], playernumber=2)
    # Monk (3) then attempts to protect player 4 (priority 2)
    monk_action = Message(priority=2, resolved=True, response=[4], playernumber=3)

    res = perform_night_actions(players, [poison_action, monk_action])

    monk = next(p for p in res if p["id"] == 3)
    target = next(p for p in res if p["id"] == 4)

    # Monk should be poisoned
    assert monk["poisoned"] is True
    # Because Monk was poisoned, their protection should NOT be applied
    assert target["protected"] is False
    assert target["dead"] is False


def test_poisoned_monk_allows_imp_kill():
    players = make_players()

    # Poisoner (2) poisons the Monk (3)
    poison_action = Message(priority=1, resolved=True, response=[3], playernumber=2)
    # Monk (3) attempts to protect player 4 (priority 2)
    monk_action = Message(priority=2, resolved=True, response=[4], playernumber=3)
    # Imp (1) attempts to kill player 4 (priority 3)
    imp_action = Message(priority=3, resolved=True, response=[4], playernumber=1)

    res = perform_night_actions(players, [poison_action, monk_action, imp_action])

    monk = next(p for p in res if p["id"] == 3)
    target = next(p for p in res if p["id"] == 4)

    # Monk is poisoned
    assert monk["poisoned"] is True
    # Monk's protection should not apply
    assert target["protected"] is False
    # Imp's kill should succeed because protection failed
    assert target["dead"] is True


def test_placeholder():
    assert True