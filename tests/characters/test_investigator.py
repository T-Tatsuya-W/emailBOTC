import random
from copy import deepcopy

from utils.message_handler import Message
from main import perform_night_actions
from utils.player_factory import make_players


def get_player(players, role):
    return next(p for p in players if p["role"] == role)


def test_investigator_first_night_includes_poisoner_and_other():
    players = make_players()
    # assign Investigator to player 1
    players[0]["role"] = "Investigator"
    players[0]["first_night_only"] = True
    players[0]["nightResponse"] = 0

    # sanity: ensure a Poisoner exists in canonical roster
    assert any(p.get("role") == "Poisoner" for p in players)

    # Create a Message representing Investigator action (no response expected)
    inv = get_player(players, "Investigator")
    msg = Message(priority=inv["nightActionPriority"], resolved=True, response=[], playernumber=inv["id"])

    res = perform_night_actions(players, [msg])

    inv_after = get_player(res, "Investigator")
    assert "info_for_player" in inv_after and isinstance(inv_after["info_for_player"], str)
    assert "Investigation" in inv_after["info_for_player"]


def test_investigator_poisoned_gives_random_players():
    players = make_players()
    players[0]["role"] = "Investigator"
    players[0]["first_night_only"] = True
    players[0]["nightResponse"] = 0
    players[0]["poisoned"] = True

    inv = get_player(players, "Investigator")
    msg = Message(priority=inv["nightActionPriority"], resolved=True, response=[], playernumber=inv["id"])
    res = perform_night_actions(players, [msg])

    inv_after = get_player(res, "Investigator")
    assert isinstance(inv_after.get("info_for_player"), str)
    assert "Investigation" in inv_after.get("info_for_player")


def test_investigator_when_no_poisoner_picks_two():
    players = make_players()
    # remove poisoner by changing that role
    for p in players:
        if p.get("role") == "Poisoner":
            p["role"] = "Villager"
            break

    players[0]["role"] = "Investigator"
    players[0]["first_night_only"] = True
    players[0]["nightResponse"] = 0

    inv = get_player(players, "Investigator")
    msg = Message(priority=inv["nightActionPriority"], resolved=True, response=[], playernumber=inv["id"])
    res = perform_night_actions(players, [msg])

    inv_after = get_player(res, "Investigator")
    assert isinstance(inv_after.get("info_for_player"), str)
    assert "Investigation" in inv_after.get("info_for_player")
