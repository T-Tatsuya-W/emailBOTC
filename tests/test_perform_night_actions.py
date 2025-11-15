"""Unit tests for `perform_night_actions` that do not need the MessageHandler.

These tests construct `Message` objects directly and call
`perform_night_actions(players, actions)` so the resolution logic can be
tested in isolation.
"""
from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def get_player(players, role):
    return next(p for p in players if p["role"] == role)


def test_imp_kills_unprotected_target():
    """imp kills unprotected target"""
    players = make_players()

    # Imp kills the Villager (target looked up dynamically)
    imp = get_player(players, "Imp")
    villager = get_player(players, "Villager")
    imp_action = Message(priority=3, resolved=True, response=[villager["id"]], playernumber=imp["id"])

    res = perform_night_actions(players, [imp_action])

    target = get_player(res, "Villager")
    assert target["dead"] is True


def test_fortune_teller_investigate_no_state_change():
    """fortune teller investigate no state change"""
    players = make_players()

    # Fortune Teller investigates Poisoner and Villager
    ft = get_player(players, "Fortune Teller")
    poisoner = get_player(players, "Poisoner")
    villager = get_player(players, "Villager")
    ft_action = Message(priority=4, resolved=True, response=[poisoner["id"], villager["id"]], playernumber=ft["id"])

    res = perform_night_actions(players, [ft_action])

    # No player state that affects game (dead/poisoned/protected) should change
    for p in res:
        assert p["dead"] is False
        assert p["poisoned"] is False
        assert p["protected"] is False

    # Fortune Teller should receive an informational reveal stored on their player state
    ft_after = get_player(res, "Fortune Teller")
    assert ft_after.get("info_for_player") is False


def test_fortune_teller_detects_imp():
    """fortune teller detects imp among targets"""
    players = make_players()

    # Fortune Teller investigates Imp and Villager
    ft = get_player(players, "Fortune Teller")
    imp = get_player(players, "Imp")
    villager = get_player(players, "Villager")
    ft_action = Message(priority=4, resolved=True, response=[imp["id"], villager["id"]], playernumber=ft["id"])

    res = perform_night_actions(players, [ft_action])

    ft_after = get_player(res, "Fortune Teller")
    assert ft_after.get("info_for_player") is True


def test_fortune_teller_red_herring_counts_as_evil():
    """fortune teller red herring counts as evil"""
    players = make_players()

    # Configure the Fortune Teller's red herring to be the Villager
    ft = get_player(players, "Fortune Teller")
    villager = get_player(players, "Villager")
    poisoner = get_player(players, "Poisoner")
    ft["red_herring"] = villager["id"]

    # Fortune Teller investigates Poisoner and Villager (Villager is red herring)
    ft_action = Message(priority=4, resolved=True, response=[poisoner["id"], villager["id"]], playernumber=ft["id"])

    res = perform_night_actions(players, [ft_action])

    ft_after = get_player(res, "Fortune Teller")
    assert ft_after.get("info_for_player") is True


def test_monk_protects_from_imp_kill():
    """monk protects from imp kill"""
    players = make_players()

    # Monk protects the Villager and Imp tries to kill the Villager
    monk = get_player(players, "Monk")
    imp = get_player(players, "Imp")
    villager = get_player(players, "Villager")
    monk_action = Message(priority=2, resolved=True, response=[villager["id"]], playernumber=monk["id"])
    imp_action = Message(priority=3, resolved=True, response=[villager["id"]], playernumber=imp["id"])

    res = perform_night_actions(players, [monk_action, imp_action])

    target = get_player(res, "Villager")
    assert target["protected"] is True
    assert target["dead"] is False


def test_poisoner_marks_target_poisoned_not_dead():
    """poisoner marks target poisoned not dead"""
    players = make_players()

    # Poisoner poisons the Villager
    poisoner = get_player(players, "Poisoner")
    villager = get_player(players, "Villager")
    poison_action = Message(priority=1, resolved=True, response=[villager["id"]], playernumber=poisoner["id"])

    res = perform_night_actions(players, [poison_action])

    target = get_player(res, "Villager")
    assert target["poisoned"] is True
    assert target["dead"] is False


def test_poisoned_monk_cannot_protect():
    """poisoned monk cannot protect"""
    # Poison the Monk and then have the Monk try to protect the Villager.
    players = make_players()

    # Poisoner poisons the Monk, then Monk attempts to protect the Villager
    poisoner = get_player(players, "Poisoner")
    monk = get_player(players, "Monk")
    villager = get_player(players, "Villager")
    poison_action = Message(priority=1, resolved=True, response=[monk["id"]], playernumber=poisoner["id"])
    monk_action = Message(priority=2, resolved=True, response=[villager["id"]], playernumber=monk["id"])

    res = perform_night_actions(players, [poison_action, monk_action])

    monk_after = get_player(res, "Monk")
    target = get_player(res, "Villager")

    # Monk should be poisoned
    assert monk_after["poisoned"] is True
    # Because Monk was poisoned, their protection should NOT be applied
    assert target["protected"] is False
    assert target["dead"] is False


def test_poisoned_monk_protection_fails_and_imp_kills_target():
    """poisoned monk protection fails and imp kills target"""
    players = make_players()

    # Poisoner poisons the Monk, Monk attempts to protect the Villager, Imp tries to kill Villager
    poisoner = get_player(players, "Poisoner")
    monk = get_player(players, "Monk")
    imp = get_player(players, "Imp")
    villager = get_player(players, "Villager")
    poison_action = Message(priority=1, resolved=True, response=[monk["id"]], playernumber=poisoner["id"])
    monk_action = Message(priority=2, resolved=True, response=[villager["id"]], playernumber=monk["id"])
    imp_action = Message(priority=3, resolved=True, response=[villager["id"]], playernumber=imp["id"])

    res = perform_night_actions(players, [poison_action, monk_action, imp_action])

    monk_after = get_player(res, "Monk")
    target = get_player(res, "Villager")

    # Monk is poisoned
    assert monk_after["poisoned"] is True
    # Monk's protection should not apply
    assert target["protected"] is False
    # Imp's kill should succeed because protection failed
    assert target["dead"] is True
