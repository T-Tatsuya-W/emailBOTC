from typing import List, Optional


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
