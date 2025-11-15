"""Compact test to validate `setup_players` with example contacts."""

import random

from utils.player_factory import setup_players


def test_setup_players_compact():
    contacts = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
        ("Dana", "dana@example.com"),
        ("Eve", "eve@example.com"),
        ("Frank", "frank@example.com"),
    ]

    players = setup_players(contacts, rng=random.Random(0))

    assert len(players) == len(contacts)
    assert {p["name"] for p in players} == {name for name, _ in contacts}
    assert {p["email"] for p in players} == {email for _, email in contacts}
