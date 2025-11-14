from __future__ import annotations

import random
from copy import deepcopy
from typing import List, Mapping, Optional, Sequence, Tuple, Union


def make_players(names: Optional[List[str]] = None, emails: Optional[List[str]] = None, default_email: Optional[str] = None):
    """Return the canonical list of players used by the demo/tests.

    Args:
        names: optional list of player names (length must match the default player count if provided).
        emails: optional list of player emails (length must match default player count if provided).
        default_email: if provided and `emails` is None, this email will be used for all players.

    The function currently returns a fixed roster of 5 players with the same
    role assignments used across the project. This keeps tests and `main.py`
    consistent while allowing callers to override names/emails if desired.
    """

    default_names = [
        "impPlayer",
        "poisonerPlayer",
        "monkPlayer",
        "villager",
        "fortuneTeller",
    ]

    # Roles and other static fields - must align with tests and main
    roles = ["Imp", "Poisoner", "Monk", "Villager", "Fortune Teller"]
    alignments = ["Evil", "Evil", "Good", "Good", "Good"]
    night_responses = [1, 1, 1, 0, 2]
    night_priorities = [3, 1, 2, 4, 4]
    can_choose_self = [True, False, False, False, False]

    names = names or default_names

    if emails is None:
        if default_email is None:
            default_email = "tobytw312@gmail.com"
        emails = [default_email] * len(names)

    players = []
    for i, name in enumerate(names, start=1):
        idx = i - 1
        player = {
            "id": i,
            "email": emails[idx],
            "name": name,
            "alignment": alignments[idx],
            "role": roles[idx],
            "drunk": False,
            "poisoned": False,
            "dead": False,
            "canVote": True,
            "protected": False,
            "nightResponse": night_responses[idx],
            "canChooseSelf": can_choose_self[idx],
            "nightActionPriority": night_priorities[idx],
        }

        # default extra fields used by tests
        if player["role"] == "Fortune Teller":
            # Assign a default red herring: the first other good player in the roster.
            red_herring_id = None
            for existing in players:
                if existing.get("alignment") == "Good" and existing.get("id") != player["id"]:
                    red_herring_id = existing["id"]
                    break

            player["red_herring"] = red_herring_id
            player["info_for_player"] = None

        players.append(player)

    return players


def _normalise_player_contacts(
    player_contacts: Union[Mapping[str, str], Sequence[Union[Tuple[str, str], Mapping[str, str]]], None],
    default_players: List[dict],
) -> List[Tuple[str, str]]:
    """Normalise caller-provided player contact details."""

    if player_contacts is None:
        return [(p["name"], p["email"]) for p in default_players]

    contacts: List[Tuple[str, str]] = []

    if isinstance(player_contacts, Mapping):
        contacts = [(name, email) for name, email in player_contacts.items()]
    else:
        for entry in player_contacts:
            if isinstance(entry, Mapping):
                name = entry.get("name")
                email = entry.get("email")
            else:
                try:
                    name, email = entry  # type: ignore[misc]
                except (TypeError, ValueError):
                    raise TypeError("Player contacts must be a mapping or an iterable of (name, email) pairs")

            if name is None or email is None:
                raise ValueError("Each player contact must include both a name and an email")

            contacts.append((str(name), str(email)))

    expected_len = len(default_players)
    if len(contacts) != expected_len:
        raise ValueError(f"Expected {expected_len} player contacts, received {len(contacts)}")

    return contacts


def setup_players(
    player_contacts: Union[Mapping[str, str], Sequence[Union[Tuple[str, str], Mapping[str, str]]], None],
    *,
    rng: Optional[random.Random] = None,
) -> List[dict]:
    """Create the canonical player set with optional caller-provided contacts.

    Args:
        player_contacts: Either a mapping of ``name -> email`` or an iterable of
            ``(name, email)`` pairs. If ``None`` the defaults from ``make_players``
            are used. The number of provided contacts must match the default
            player count.
        rng: Optional :class:`random.Random` instance used to shuffle the seating
            order. If omitted a new ``Random`` instance is created.

    Returns:
        A list of player dictionaries equivalent to ``make_players`` but with the
        seating order randomised. IDs are reassigned sequentially after the
        shuffle.
    """

    base_players = [deepcopy(player) for player in make_players()]
    contacts = _normalise_player_contacts(player_contacts, base_players)

    for player, (name, email) in zip(base_players, contacts):
        player["name"] = name
        player["email"] = email

    rng = rng or random.Random()
    rng.shuffle(base_players)

    for idx, player in enumerate(base_players, start=1):
        player["id"] = idx

    return base_players
