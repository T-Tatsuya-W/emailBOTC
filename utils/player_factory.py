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
        "player1name",
        "player2name",
        "player3name",
        "player4name",
        "player5name",
        "player6name",
    ]

    # Roles and other static fields - must align with tests and main
    roles = ["Imp", "Poisoner", "Monk", "Soldier", "Villager", "Fortune Teller"]
    alignments = ["Evil", "Evil", "Good", "Good", "Good", "Good"]
    # night_responses: number of integer responses expected from each role
    night_responses = [1, 1, 1, 0, 0, 2]
    night_priorities = [3, 1, 2, 4, 4, 4]
    can_choose_self = [True, False, False, False, False, False]

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
            # first-night behaviour flags (defaults)
            "first_night_only": False,
            "skip_first_night": False,
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

        # Role-specific first-night rules: Imp and Monk do not act on the first night
        if player["role"] == "Imp":
            player["skip_first_night"] = True
        if player["role"] == "Monk":
            player["skip_first_night"] = True

        players.append(player)

    # Note: role-specific default fields have already been set above. Keep
    # Soldier's `protected` flag configurable by callers/tests rather than
    # forcing it here so tests can explicitly set expectations.

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

    # If the caller provided more contacts than the canonical roster we
    # expand the base_players with additional Villagers so every contact
    # is represented. If fewer contacts are provided we trim the roster
    # to match the provided contacts.
    if len(contacts) > len(base_players):
        extra = len(contacts) - len(base_players)
        for i in range(extra):
            new_id = len(base_players) + 1
            player = {
                "id": new_id,
                "email": None,
                "name": f"player{new_id}name",
                "alignment": "Good",
                "role": "Villager",
                "drunk": False,
                "poisoned": False,
                "dead": False,
                "canVote": True,
                "protected": False,
                "nightResponse": 0,
                "canChooseSelf": False,
                    "nightActionPriority": 4,
                    "_is_extra": True,
            }
            base_players.append(player)
    elif len(contacts) < len(base_players):
        base_players = base_players[: len(contacts)]

    for player, (name, email) in zip(base_players, contacts):
        player["name"] = name
        player["email"] = email

    rng = rng or random.Random()
    rng.shuffle(base_players)

    for idx, player in enumerate(base_players, start=1):
        player["id"] = idx

    # If the caller requested the canonical roster size (six players) make
    # sure the live-game roster prefers the Investigator role rather than
    # leaving an unused Villager slot. We do this only for the `setup_players`
    # runtime path so unit tests that call `make_players()` directly keep
    # the previous canonical data structure.
    canonical_count = len(make_players())
    if len(contacts) == canonical_count:
        # Find the first Villager and replace with Investigator for play.
        for player in base_players:
            if player.get("role") == "Villager":
                player["role"] = "Investigator"
                player["alignment"] = "Good"
                player["nightResponse"] = 0
                player["nightActionPriority"] = 4
                player["canChooseSelf"] = False
                player["first_night_only"] = True
                break

    # If the caller did not request the canonical roster size, apply a
    # simplified role assignment:
    # - exactly one Imp
    # - exactly one Poisoner
    # - choose 3 distinct Good roles from a pool and assign exactly one of each
    # - remaining players become Villagers
    canonical_count = len(make_players())
    if len(contacts) != canonical_count:
        # pick two distinct players for Imp and Poisoner, but only within
        # the first `canonical_count` slots so any extra players remain
        # Villagers. This ensures extra contacts beyond the canonical roster
        # size are kept as Villagers.
        # Determine which positions correspond to original canonical slots
        # (extra appended players are flagged with `_is_extra`). We want to
        # ensure special-role assignment only applies to the original roster
        # so extras remain Villagers even after shuffling.
        assignable_positions = [i for i, p in enumerate(base_players) if not p.get("_is_extra", False)]
        if not assignable_positions:
            assignable_positions = list(range(min(len(base_players), canonical_count)))
        rng.shuffle(assignable_positions)
        imp_idx = assignable_positions[0]
        poisoner_idx = assignable_positions[1] if len(assignable_positions) > 1 else None

        # Pool of candidate Good roles (some may be placeholders)
        # We will assign as many distinct roles from this pool as possible
        # (one of each). Only if there are more players than roles will the
        # remaining players become Villagers.
        good_roles_pool = ["Fortune Teller", "Monk", "Soldier", "Investigator"]
        rng.shuffle(good_roles_pool)

        # Prepare an iterator over the shuffled good roles; we'll consume one
        # role per non-Imp/non-Poisoner player until the pool is exhausted.
        role_iter = iter(good_roles_pool)

        for i, player in enumerate(base_players):
            # assign Imp and Poisoner (only within assignable positions)
            if i == imp_idx:
                player["role"] = "Imp"
                player["alignment"] = "Evil"
                player["nightResponse"] = 1
                player["nightActionPriority"] = 3
                player["canChooseSelf"] = True
                player.setdefault("first_night_only", False)
                player["skip_first_night"] = True
            elif i == poisoner_idx:
                player["role"] = "Poisoner"
                player["alignment"] = "Evil"
                player["nightResponse"] = 1
                player["nightActionPriority"] = 1
                player["canChooseSelf"] = False
                player.setdefault("first_night_only", False)
                player.setdefault("skip_first_night", False)
            else:
                # If this slot is NOT one of the assignable positions, treat
                # it as an extra player and make it a Villager. Otherwise
                # consume the next distinct good role from the pool.
                if i not in assignable_positions:
                    role = "Villager"
                else:
                    try:
                        role = next(role_iter)
                    except StopIteration:
                        role = "Villager"

                player["role"] = role
                player["alignment"] = "Good"

                # Soldier does not require a numeric response; Monk expects 1,
                # Fortune Teller expects 2. Investigator expects 0.
                if role == "Fortune Teller":
                    player["nightResponse"] = 2
                elif role == "Monk":
                    player["nightResponse"] = 1
                elif role == "Investigator":
                    player["nightResponse"] = 0
                else:
                    player["nightResponse"] = 0

                # set priority: Monk(2), FT(4), Soldier(4), placeholders default to 4
                player["nightActionPriority"] = 2 if role == "Monk" else 4
                player["canChooseSelf"] = True if role == "Soldier" else False

                # Investigator only acts on the first night
                if role == "Investigator":
                    player["first_night_only"] = True

                # Monk does not act on the first night in our ruleset
                if role == "Monk":
                    player["skip_first_night"] = True
                else:
                    player.setdefault("skip_first_night", False)

            # Ensure default first-night flags exist for other role paths
            player.setdefault("first_night_only", False)
            player.setdefault("skip_first_night", False)

            # role-specific defaults
            if player["role"] == "Soldier":
                player["protected"] = True

            if player["role"] == "Fortune Teller":
                # Assign a default red herring: the first other good player in the roster.
                red_herring_id = None
                for existing in base_players:
                    if existing.get("alignment") == "Good" and existing.get("id") != player.get("id"):
                        red_herring_id = existing.get("id")
                        break
                player["red_herring"] = red_herring_id
                player["info_for_player"] = None

            # common defaults
            player.setdefault("drunk", False)
            player.setdefault("poisoned", False)
            player.setdefault("dead", False)
            player.setdefault("canVote", True)
            player.setdefault("protected", False)

    return base_players
