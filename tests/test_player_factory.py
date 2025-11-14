"""Tests for player factory helpers."""

import random

import pytest

from utils.player_factory import make_players, setup_players


def extract_roles():
    return [player["role"] for player in make_players()]


def test_setup_players_randomises_with_list():
    contacts = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
        ("Dana", "dana@example.com"),
        ("Eve", "eve@example.com"),
    ]

    rng = random.Random(42)
    players = setup_players(contacts, rng=rng)

    assert len(players) == len(contacts)
    assert {p["name"] for p in players} == {name for name, _ in contacts}
    assert {p["email"] for p in players} == {email for _, email in contacts}
    assert {p["role"] for p in players} == set(extract_roles())
    assert [p["id"] for p in players] == list(range(1, len(contacts) + 1))

    expected_order = list(range(len(contacts)))
    random.Random(42).shuffle(expected_order)
    expected_names = [contacts[i][0] for i in expected_order]
    assert [p["name"] for p in players] == expected_names


def test_setup_players_accepts_mapping():
    contacts = {
        "Alice": "alice@example.com",
        "Bob": "bob@example.com",
        "Charlie": "charlie@example.com",
        "Dana": "dana@example.com",
        "Eve": "eve@example.com",
    }

    rng = random.Random(3)
    players = setup_players(contacts, rng=rng)

    ordered_contacts = list(contacts.items())
    expected_order = list(range(len(ordered_contacts)))
    random.Random(3).shuffle(expected_order)
    expected_names = [ordered_contacts[i][0] for i in expected_order]

    assert [p["name"] for p in players] == expected_names
    assert {p["email"] for p in players} == {email for _, email in ordered_contacts}


def test_setup_players_validates_length():
    contacts = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
    ]

    with pytest.raises(ValueError):
        setup_players(contacts)
