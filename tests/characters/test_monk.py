"""Monk-related tests.

Duplicated tests that involve other roles are present here as well for clear
reading by role.
"""
from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def get_player(players, role):
    return next(p for p in players if p["role"] == role)


def test_monk_protects():
    players = make_players()

    monk = get_player(players, "Monk")
    imp = get_player(players, "Imp")
    villager = get_player(players, "Villager")

    monk_action = Message(
        priority=2,
        resolved=True,
        response=[villager["id"]],
        playernumber=monk["id"],
    )
    imp_action = Message(
        priority=3,
        resolved=True,
        response=[villager["id"]],
        playernumber=imp["id"],
    )

    res = perform_night_actions(players, [monk_action, imp_action])

    target = get_player(res, "Villager")
    assert target["protected"] is True
    assert target["dead"] is False


def test_monk_poisoned_cannot_protect():
    # Poison the Monk (id 3) and then have the Monk try to protect player 4.
    players = make_players()

    poisoner = get_player(players, "Poisoner")
    monk = get_player(players, "Monk")
    villager = get_player(players, "Villager")

    poison_action = Message(
        priority=1,
        resolved=True,
        response=[monk["id"]],
        playernumber=poisoner["id"],
    )
    monk_action = Message(
        priority=2,
        resolved=True,
        response=[villager["id"]],
        playernumber=monk["id"],
    )

    res = perform_night_actions(players, [poison_action, monk_action])

    monk = get_player(res, "Monk")
    target = get_player(res, "Villager")

    # Monk should be poisoned
    assert monk["poisoned"] is True
    # Because Monk was poisoned, their protection should NOT be applied
    assert target["protected"] is False
    assert target["dead"] is False


def test_poisoned_monk_allows_imp_kill():
    players = make_players()

    poisoner = get_player(players, "Poisoner")
    monk = get_player(players, "Monk")
    imp = get_player(players, "Imp")
    villager = get_player(players, "Villager")

    poison_action = Message(
        priority=1,
        resolved=True,
        response=[monk["id"]],
        playernumber=poisoner["id"],
    )
    monk_action = Message(
        priority=2,
        resolved=True,
        response=[villager["id"]],
        playernumber=monk["id"],
    )
    imp_action = Message(
        priority=3,
        resolved=True,
        response=[villager["id"]],
        playernumber=imp["id"],
    )

    res = perform_night_actions(players, [poison_action, monk_action, imp_action])

    monk = get_player(res, "Monk")
    target = get_player(res, "Villager")

    # Monk is poisoned
    assert monk["poisoned"] is True
    # Monk's protection should not apply
    assert target["protected"] is False
    # Imp's kill should succeed because protection failed
    assert target["dead"] is True
