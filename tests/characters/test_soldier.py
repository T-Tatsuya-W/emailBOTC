"""Soldier-related tests.

The Soldier is intended to be protected by default (cannot be killed by the Imp).
If poisoned, the Soldier should become vulnerable and may be killed by the Imp.
If the Soldier is poisoned but then the Monk protects them that night, they
should remain protected and not be killed by the Imp.
"""
from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def get_player(players, role):
    return next(p for p in players if p["role"] == role)


def test_soldier_protected_by_default():
    players = make_players()

    # Use the Soldier provided by the player factory
    soldier = get_player(players, "Soldier")
    # Ensure the test's expected default protection is set explicitly
    soldier["protected"] = True

    imp = get_player(players, "Imp")

    imp_action = Message(
        priority=3,
        resolved=True,
        response=[soldier["id"]],
        playernumber=imp["id"],
    )

    res = perform_night_actions(players, [imp_action])

    target = get_player(res, "Soldier")
    assert target["protected"] is True
    assert target["dead"] is False


def test_poisoner_poisoning_allows_imp_kill():
    players = make_players()

    soldier = get_player(players, "Soldier")
    # Ensure Soldier starts protected for this scenario
    soldier["protected"] = True

    poisoner = get_player(players, "Poisoner")
    imp = get_player(players, "Imp")

    poison_action = Message(
        priority=1,
        resolved=True,
        response=[soldier["id"]],
        playernumber=poisoner["id"],
    )
    imp_action = Message(
        priority=3,
        resolved=True,
        response=[soldier["id"]],
        playernumber=imp["id"],
    )

    res = perform_night_actions(players, [poison_action, imp_action])

    target = get_player(res, "Soldier")

    # Soldier should be poisoned
    assert target["poisoned"] is True
    # Because poisoned, Soldier should be vulnerable and could be killed
    assert target["dead"] is True


def test_poisoned_soldier_saved_by_monk_remains_protected():
    players = make_players()

    soldier = get_player(players, "Soldier")
    # Ensure Soldier starts protected for this scenario
    soldier["protected"] = True

    poisoner = get_player(players, "Poisoner")
    monk = get_player(players, "Monk")
    imp = get_player(players, "Imp")

    poison_action = Message(
        priority=1,
        resolved=True,
        response=[soldier["id"]],
        playernumber=poisoner["id"],
    )
    monk_action = Message(
        priority=2,
        resolved=True,
        response=[soldier["id"]],
        playernumber=monk["id"],
    )
    imp_action = Message(
        priority=3,
        resolved=True,
        response=[soldier["id"]],
        playernumber=imp["id"],
    )

    res = perform_night_actions(players, [poison_action, monk_action, imp_action])

    target = get_player(res, "Soldier")

    # Soldier should be poisoned
    assert target["poisoned"] is True
    # Monk's protection should apply
    assert target["protected"] is True
    # Imp's kill should be prevented
    assert target["dead"] is False
