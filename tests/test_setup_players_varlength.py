"""Tests for `setup_players` behaviour with different contact list sizes.

Current implementation expects the contact list length to match the canonical
roster returned by `make_players()`. These tests encode that expectation for
various sizes so we can later update behaviour and tests together when
supporting flexible roster sizes.
"""

import pytest

from utils.player_factory import setup_players, make_players


def make_contacts(n):
    return [(f"P{i}", f"p{i}@example.com") for i in range(1, n + 1)]


def test_setup_players_accepts_canonical_size():
    default_count = len(make_players())
    contacts = make_contacts(default_count)

    players = setup_players(contacts)

    assert len(players) == default_count
    assert {p["email"] for p in players} == {email for _, email in contacts}


@pytest.mark.parametrize("size", [5, 6, 7, 8, 10])
def test_setup_players_accepts_various_sizes(size):
    # The factory should accept various contact list sizes. If the list is
    # longer than the canonical roster the extra players should be Villagers.
    contacts = make_contacts(size)

    players = setup_players(contacts)
    assert len(players) == size

    if size > len(make_players()):
        # Extra players beyond canonical roster should increase the total
        # number of Villagers by at least the extra amount (shuffle may
        # mix players, so we count totals rather than rely on ordering).
        extra_needed = size - len(make_players())
        original_villagers = sum(1 for p in make_players() if p["role"] == "Villager")
        villagers_after = sum(1 for p in players if p["role"] == "Villager")
        assert villagers_after >= original_villagers + extra_needed

    # For all accepted sizes (<10) ensure exactly one Imp and one Poisoner
    assert sum(1 for p in players if p["role"] == "Imp") == 1
    assert sum(1 for p in players if p["role"] == "Poisoner") == 1

    # Ensure exactly three non-Villager Good roles were assigned (each unique)
    special_good = [p["role"] for p in players if p["role"] not in ("Imp", "Poisoner", "Villager")]
    assert len(special_good) == 3
    assert len(set(special_good)) == 3
