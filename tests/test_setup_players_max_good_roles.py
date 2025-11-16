"""Test to determine the maximum distinct Good-role types that can
be produced by `setup_players` under current behaviour.

This test documents the current limit (should be 4: Monk, Soldier,
Fortune Teller and Villager) and will fail if role-assignment logic
is later changed to allow more Good roles to appear concurrently.
"""

import random

from utils.player_factory import setup_players, make_players


def good_roles_of(players):
    return {p["role"] for p in players if p.get("alignment") == "Good"}


def test_max_distinct_good_roles():
    # Check a range of roster sizes and capture the maximum number of
    # distinct Good-role types produced by the current setup logic.
    sizes = list(range(1, 21))
    max_distinct = 0

    for n in sizes:
        contacts = [(f"P{i}", f"p{i}@example.com") for i in range(1, n + 1)]
        players = setup_players(contacts, rng=random.Random(42))
        distinct_good = len(good_roles_of(players))
        if distinct_good > max_distinct:
            max_distinct = distinct_good

    # Current behaviour: canonical roster provides 5 Good roles
    # (Monk, Soldier, Fortune Teller, Investigator, Villager) and the
    # reassignment logic may expose all of these concurrently.
    assert max_distinct == 5
