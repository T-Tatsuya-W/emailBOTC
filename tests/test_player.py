"""Tests for the new minimal Player API."""
from game.player import Player

def test_player_initial_attributes_and_defaults():
    p = Player("Alice", "alice@example.com", character="Villager")
    # player_id should exist and be a non-empty string
    assert isinstance(p.player_id, str) and p.player_id
    assert p.playername == "Alice"
    assert p.player_email == "alice@example.com"
    assert p.character == "Villager"
    assert p.alive is True
    assert p.is_alive() is True
    # default can_vote should be True
    assert p.can_vote is True
    # default can_nominate should be True
    assert p.can_nominate is True
    # default evil should be False
    assert p.evil is False
    # default status effects
    assert p.drunk is False
    assert p.poisoned is False


def test_kill_marks_dead_and_is_alive_false():
    p = Player("Bob", "bob@example.com")
    assert p.alive is True
    assert p.can_nominate is True
    p.kill()
    assert p.alive is False
    assert p.is_alive() is False
    assert p.can_nominate is False


def test_can_vote_toggle_and_repr_contains_fields():
    p = Player("Cara", "cara@example.com", character=None, can_vote=False)
    assert p.can_vote is False
    # can_nominate defaults to True unless changed
    assert p.can_nominate is True
    # should include key fields in representation for debugging
    r = repr(p)
    assert "Cara" in r
    assert "cara@example.com" in r
    assert "can_vote=False" in r
    assert "can_nominate=True" in r
    # evil defaults to False and should be visible in repr
    assert "evil=False" in r
    assert "drunk=False" in r
    assert "poisoned=False" in r


def test_dead_players_cannot_nominate():
    """Explicit test ensuring killed/dead players cannot nominate."""
    p = Player("Dylan", "dylan@example.com")
    # sanity precondition
    assert p.alive is True
    assert p.can_nominate is True
    # kill and ensure nomination is disabled
    p.kill()
    assert p.alive is False
    assert p.can_nominate is False


def test_evil_flag_can_be_set_and_shown_in_repr():
    p = Player("Eve", "eve@example.com", evil=True)
    assert p.evil is True
    assert "evil=True" in repr(p)


def test_status_effects_can_be_set_and_shown_in_repr():
    p = Player("Frank", "frank@example.com", drunk=True, poisoned=True)
    assert p.drunk is True
    assert p.poisoned is True
    r = repr(p)
    assert "drunk=True" in r
    assert "poisoned=True" in r


