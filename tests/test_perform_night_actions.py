import pytest
pytest.skip("legacy duplicate - tests moved to tests/characters/", allow_module_level=True)

"""Unit tests for `perform_night_actions` that do not need the MessageHandler.

These tests construct `Message` objects directly and call
`perform_night_actions(players, actions)` so the resolution logic can be
tested in isolation.
"""
from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def test_imp_kills_unprotected_target():
    """imp kills unprotected target"""
    players = make_players()

    # Imp (1) kills player 4
    imp_action = Message(priority=3, resolved=True, response=[4], playernumber=1)

    res = perform_night_actions(players, [imp_action])

    target = next(p for p in res if p["id"] == 4)
    assert target["dead"] is True


def test_fortune_teller_investigate_no_state_change():
    """fortune teller investigate no state change"""
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


def test_fortune_teller_detects_imp():
    """fortune teller detects imp among targets"""
    players = make_players()

    # Fortune Teller (5) investigates players 1 (Imp) and 4
    ft_action = Message(priority=4, resolved=True, response=[1, 4], playernumber=5)

    res = perform_night_actions(players, [ft_action])

    ft = next(p for p in res if p["id"] == 5)
    assert ft.get("info_for_player") == "at least one is evil"


def test_fortune_teller_red_herring_counts_as_evil():
    """fortune teller red herring counts as evil"""
    players = make_players()

    # Configure the Fortune Teller's red herring to be player 4
    ft = next(p for p in players if p["role"] == "Fortune Teller")
    ft["red_herring"] = 4

    # Fortune Teller (5) investigates players 2 and 4 (both non-Imp, but 4 is red herring)
    ft_action = Message(priority=4, resolved=True, response=[2, 4], playernumber=5)

    res = perform_night_actions(players, [ft_action])

    ft_after = next(p for p in res if p["id"] == 5)
    assert ft_after.get("info_for_player") == "at least one is evil"


def test_monk_protects_from_imp_kill():
    """monk protects from imp kill"""
    players = make_players()

    # Monk (3) protects player 4 (priority 2)
    monk_action = Message(priority=2, resolved=True, response=[4], playernumber=3)
    # Imp (1) tries to kill player 4 (priority 3)
    imp_action = Message(priority=3, resolved=True, response=[4], playernumber=1)

    res = perform_night_actions(players, [monk_action, imp_action])

    target = next(p for p in res if p["id"] == 4)
    assert target["protected"] is True
    assert target["dead"] is False


def test_poisoner_marks_target_poisoned_not_dead():
    """poisoner marks target poisoned not dead"""
    players = make_players()

    # Poisoner (2) poisons player 4
    poison_action = Message(priority=1, resolved=True, response=[4], playernumber=2)

    res = perform_night_actions(players, [poison_action])

    target = next(p for p in res if p["id"] == 4)
    assert target["poisoned"] is True
    assert target["dead"] is False


def test_poisoned_monk_cannot_protect():
    """poisoned monk cannot protect"""
    # Poison the Monk (id 3) and then have the Monk try to protect player 4.
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


def test_poisoned_monk_protection_fails_and_imp_kills_target():
    """poisoned monk protection fails and imp kills target"""
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
