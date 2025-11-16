"""Skeleton game loop entrypoint.

This file is intentionally minimal. It accepts a single integer CLI
parameter and dispatches to the nightphase implementation which lives in
`utils/nightphase.py` after refactoring.
"""
from __future__ import annotations

import sys
from typing import Optional, Sequence, Tuple

from utils.player_factory import make_players, setup_players
from utils.nightphase import nightphase, perform_night_actions, get_player_by_number, first_nightphase
from utils.dayphase import dayphase

# Re-export helpers for older imports/tests that expect them on `main`.
__all__ = ["nightphase", "perform_night_actions", "get_player_by_number"]


def parse_cli(argv: Optional[list] = None) -> Optional[str]:
    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        return None

    arg = argv[1]
    if arg in ("-h", "--help"):
        print("Usage: python main.py <option_int>")
        raise SystemExit(0)

    # Support a "d" parameter to run with the default player set.
    if arg in ("d", "-d", "D"):
        return "d"

    # Non-"d" arguments are treated as interactive mode trigger (return string).
    return arg


def get_player_info() -> Sequence[Tuple[str, str]]:
    """Prompt user for a player count, then collect player names and emails.

    Returns a list of (name, email) tuples suitable for `setup_players`.
    The current game uses a fixed role roster; the function therefore
    enforces the canonical player count and asks the user to accept the
    default if they attempt a different size.
    """
    default_players = make_players()
    default_count = len(default_players)

    while True:
        try:
            raw = input(f"Number of players [default {default_count}]: ").strip()
        except EOFError:
            print("\nNo input received; using default players.")
            raw = ""

        if raw == "":
            num = default_count
            break

        try:
            num = int(raw)
        except ValueError:
            print("Please enter a valid integer (or press Enter to accept default).")
            continue

        # Enforce a minimum number of players for the game
        if num < 5:
            print("Minimum number of players is 5. Please enter a larger number.")
            continue
        # Enforce a maximum number of players for the CLI game definition
        if num >= 10:
            print("Maximum number of players for this CLI mode is 9. Please enter a smaller number.")
            continue

        break

    contacts = []
    for i in range(1, num + 1):
        default_name = default_players[i - 1]["name"] if i - 1 < len(default_players) else f"Player{i}"
        try:
            name = input(f"Player {i} name [default: {default_name}]: ").strip() or default_name
        except EOFError:
            name = default_name

        try:
            email = input(f"Player {i} email [default: {default_players[i - 1]['email']}]: ").strip() or default_players[i - 1]["email"]
        except EOFError:
            email = default_players[i - 1]["email"]

        contacts.append((name, email))

    return contacts


def main() -> None:
    opt = parse_cli()
    default_email = "tobytw312@gmail.com"

    if opt == "d":
        players = make_players(default_email=default_email)
    else:
        contacts = get_player_info()
        players = setup_players(contacts)

    # Debug: print every player and all stored values before starting rounds
    print("\n--- Players (initial) ---")
    for p in players:
        print(p)
    print("--- end players ---\n")

    round_num = 1
    while True:
        print(f"\n=== Night {round_num} ===")
        if round_num == 1:
            players = first_nightphase(players)
        else:
            players = nightphase(players, night_number=round_num)

        # Run day phase (currently a mock that prints player states)
        print(f"\n=== Day {round_num} ===")
        # Run dayphase and wait longer for player acknowledgements/nominations
        players = dayphase(players, day_number=round_num)

        # Check win state: if exactly 2 players are alive and one is the Imp,
        # Evil wins. Print a terminal message and end the game.
        alive = [p for p in players if not p.get("dead")]
        alive_count = len(alive)
        if alive_count == 2 and any(p.get("role") == "Imp" for p in alive):
            print("Game over: Evil wins (Imp remains among two alive players).")
            break

        round_num += 1

    # Final player states
    print("\n--- Final players ---")
    for p in players:
        print(p)
    print("--- end players ---\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user")
        sys.exit(1)

