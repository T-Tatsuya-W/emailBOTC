"""Fortune Teller tests.

Includes tests for reveal behaviour and red-herring handling.
"""
from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def get_player(players, role):
    return next(p for p in players if p["role"] == role)


def test_ft_no_state_change():
    players = make_players()

    fortune_teller = get_player(players, "Fortune Teller")
    poisoner = get_player(players, "Poisoner")
    villager = get_player(players, "Villager")

    ft_action = Message(
        priority=4,
        resolved=True,
        response=[poisoner["id"], villager["id"]],
        playernumber=fortune_teller["id"],
    )

    res = perform_night_actions(players, [ft_action])

    # No player state that affects game (dead/poisoned/protected) should change
    for p in res:
        assert p["dead"] is False
        assert p["poisoned"] is False
        assert p["protected"] is False

    # Fortune Teller should receive an informational reveal stored on their player state
    ft = get_player(res, "Fortune Teller")
    assert ft.get("info_for_player") is False


def test_ft_detects_imp():
    players = make_players()

    fortune_teller = get_player(players, "Fortune Teller")
    imp = get_player(players, "Imp")
    villager = get_player(players, "Villager")

    ft_action = Message(
        priority=4,
        resolved=True,
        response=[imp["id"], villager["id"]],
        playernumber=fortune_teller["id"],
    )

    res = perform_night_actions(players, [ft_action])

    ft = get_player(res, "Fortune Teller")
    assert ft.get("info_for_player") is True


def test_ft_red_herring_counts():
    players = make_players()

    fortune_teller = get_player(players, "Fortune Teller")
    villager = get_player(players, "Villager")
    poisoner = get_player(players, "Poisoner")

    fortune_teller["red_herring"] = villager["id"]

    ft_action = Message(
        priority=4,
        resolved=True,
        response=[poisoner["id"], villager["id"]],
        playernumber=fortune_teller["id"],
    )

    res = perform_night_actions(players, [ft_action])

    ft_after = get_player(res, "Fortune Teller")
    assert ft_after.get("info_for_player") is True


def test_ft_poisoned_returns_incorrect_info():
    players = make_players()

    # Poison the Fortune Teller directly for the test scenario
    ft = next(p for p in players if p["role"] == "Fortune Teller")
    ft["poisoned"] = True

    # Fortune Teller investigates the Imp and the Villager; being poisoned
    # should invert the returned informational reveal.
    imp = get_player(players, "Imp")
    villager = get_player(players, "Villager")
    ft_action = Message(priority=4, resolved=True, response=[imp["id"], villager["id"]], playernumber=ft["id"])

    res = perform_night_actions(players, [ft_action])

    ft_after = get_player(res, "Fortune Teller")
    assert ft_after.get("info_for_player") is False


def test_ft_default_red_herring_is_good_player():
    players = make_players()

    ft = next(p for p in players if p["role"] == "Fortune Teller")
    assert ft.get("red_herring") is not None

    red_herring_player = next(p for p in players if p["id"] == ft["red_herring"])
    assert red_herring_player["alignment"] == "Good"

    # Fortune Teller investigates their red herring and another good player
    other_good = next(p for p in players if p["role"] == "Villager")
    ft_action = Message(priority=4, resolved=True, response=[ft["red_herring"], other_good["id"]], playernumber=ft["id"])

    res = perform_night_actions(players, [ft_action])

    ft_after = get_player(res, "Fortune Teller")
    assert ft_after.get("info_for_player") is True
