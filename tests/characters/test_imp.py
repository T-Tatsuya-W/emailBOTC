"""Imp-related tests (each test's first docstring line is used as the display name).

These tests exercise imp behaviour and any cross-role interactions where the
Imp participates. Tests involving multiple roles are duplicated in the other
role-specific files as well (per repository policy requested by the maintainer).
"""
from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def test_imp_kill():
    players = make_players()

    # Imp (1) kills player 4
    imp_action = Message(priority=3, resolved=True, response=[4], playernumber=1)

    res = perform_night_actions(players, [imp_action])

    target = next(p for p in res if p["id"] == 4)
    assert target["dead"] is True


def test_monk_protects():
    players = make_players()

    # Monk (3) protects player 4 (priority 2)
    monk_action = Message(priority=2, resolved=True, response=[4], playernumber=3)
    # Imp (1) tries to kill player 4 (priority 3)
    imp_action = Message(priority=3, resolved=True, response=[4], playernumber=1)

    res = perform_night_actions(players, [monk_action, imp_action])

    target = next(p for p in res if p["id"] == 4)
    assert target["protected"] is True
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
