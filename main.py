"""Skeleton game loop entrypoint.

This file is intentionally minimal. It accepts a single integer CLI
parameter and dispatches to a placeholder `run_option` function where
game phases (night/day/etc.) will be wired in later.

The script will exit with code 2 for invalid usage or non-integer args.
"""
from __future__ import annotations

import sys
from typing import Optional

from utils.email_handler import EmailHandler
from utils.message_handler import Message, MessageHandler
from utils.player_factory import make_players
from typing import Optional, Dict, Any



def parse_cli(argv: Optional[list] = None) -> Optional[int]:
    """Parse command-line args and return the integer option or None.

    If no parameter is provided, return None to indicate default behaviour.
    This function purposely does not exit the process - callers may decide
    how to handle missing/invalid parameters. Help flags still print usage
    and exit.
    """
    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        # No argument provided; caller will handle default/run-without-param.
        return None

    arg = argv[1]
    if arg in ("-h", "--help"):
        print("Usage: python main.py <option_int>")
        raise SystemExit(0)

    try:
        opt = int(arg)
    except ValueError:
        # Invalid integer - treat as no parameter for now.
        print(f"Invalid integer parameter: {arg!r}; proceeding without parameter.")
        return None

    return opt


def main() -> None:
    opt = parse_cli() # tries to parse integer parameter. 
    default_email = "tobytw312@gmail.com"

    # Create the canonical player roster using the shared factory. Callers can
    # override names/emails in the future; for now we use the default email for
    # all players to keep parity with earlier hard-coded behaviour.
    players = make_players(default_email=default_email)

    players = nightphase(players)
    print(players)





def nightphase(
    players: list,
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
) -> list:
    """Run a simplified night phase.

    This function now accepts optional `message_handler` and `email_handler`
    parameters so test code can inject mocks. If a handler is not provided the
    function will construct the default implementations.

    Args:
        players: list of player dicts.
        message_handler: optional MessageHandler instance to use.
        email_handler: optional EmailHandler instance to use (used to create a
                       MessageHandler if message_handler is not provided).

    Returns:
        The (possibly mutated) players list.
    """

    print("Starting night phase with players:")

    player_states = ""
    for player in players:
        player_states += f"- {player['name']} (is {'dead' if player['dead'] else 'alive'})\n"

    print(player_states)

    # For compatibility, nightphase now delegates to two helper functions:
    #  - get_night_actions(...) -> list[Message]
    #  - perform_night_actions(players, actions) -> players
    print("Starting night phase with players:")

    player_states = ""
    for player in players:
        player_states += f"- {player['name']} (is {'dead' if player['dead'] else 'alive'})\n"

    print(player_states)

    actions = get_night_actions(players, message_handler=message_handler, email_handler=email_handler)
    return perform_night_actions(players, actions)


def get_night_actions(
    players: list,
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
    poll_every: int = 1,
    poll_for: int = 1000,
) -> list[Message]:
    """Construct night prompts, send them and collect resolved Message actions.

    Returns a list of Message objects which have `response` populated and
    `resolved` set according to the MessageHandler logic.
    """
    # Build messages for each player
    messages: list[Message] = []
    player_states = ""
    for player in players:
        player_states += f"- {player['name']} (is {'dead' if player['dead'] else 'alive'})\n"

    for player in players:
        subject = "Night Phase Actions"
        body = (
            f"Hello {player['name']},\nIt's night time! current players:\n{player_states}\n "
            f"Please respond with your actions. You need to respond with {player['nightResponse']} integer(s)."
        )
        message = Message(
            priority=player['nightActionPriority'],
            address=player['email'],
            subject=subject + "player" + str(player['id']),
            body=body,
            resolved=False,
            response=[],
            playernumber=player["id"],
            responseBody="",
            expected_response_number=player["nightResponse"],
            playerName=player["name"],
            canChooseSelf=player["canChooseSelf"],
        )
        messages.append(message)

    # Prepare handlers: allow injection for testing, otherwise construct defaults
    if email_handler is None:
        email_handler = EmailHandler()

    if message_handler is None:
        message_handler = MessageHandler(email_handler, messages, max_player_id=len(players))
    else:
        # ensure the provided handler uses this run's messages and max_player_id
        message_handler.messages = messages
        message_handler.max_player_id = len(players)

    responses = message_handler.send_and_resolve_all(messages, poll_every=poll_every, poll_for=poll_for)
    return responses


def perform_night_actions(players: list, responses: list[Message]) -> list:
    """Apply actions (responses) to the players list according to priority.

    This function contains the role resolution logic previously embedded in
    `nightphase`. It mutates and returns the players list.
    """
    # Process resolved actions by priority (demo logic)
    for priority in range(1, 5):
        for action in [a for a in responses if getattr(a, "priority", None) == priority]:
            player = get_player_by_number(players, action.playernumber)
            print(f"Processing actions for Player {action.playernumber} ({player['name']}): {action.response}")
            match player['role']:
                case "Imp":
                    target_id = action.response[0] if action.response else None
                    target_player = get_player_by_number(players, target_id) if target_id else None
                    if target_player and not target_player['dead']:
                        # Respect protection: a protected player cannot be killed
                        if target_player.get('protected'):
                            print(f" - Imp {player['name']}'s target {target_player['name']} was protected; kill prevented.")
                        else:
                            target_player['dead'] = True
                            print(f" - Imp {player['name']} has killed {target_player['name']}.")
                    else:
                        print(f" - Imp {player['name']}'s target is invalid or already dead.")

                case "Poisoner":
                    # Clear previous poisoned flags for this night
                    for p in players:
                        p['poisoned'] = False

                    # Poisoner marks target as poisoned; poisoning does not
                    # immediately kill the target (it will affect later logic).
                    target_id = action.response[0] if action.response else None
                    target_player = get_player_by_number(players, target_id) if target_id else None
                    if target_player and not target_player['dead']:
                        target_player['poisoned'] = True
                        print(f" - Poisoner {player['name']} has poisoned {target_player['name']}.")
                    else:
                        print(f" - Poisoner {player['name']}'s target is invalid or already dead.")

                case "Monk":
                    for p in players:
                        p['protected'] = False
                        if p['role'] == 'Soldier':
                            p['protected'] = True

                    # If the monk is poisoned they cannot successfully protect
                    if player.get('poisoned'):
                        print(f" - Monk {player['name']} is poisoned and cannot protect anyone.")
                        continue

                    target_id = action.response[0] if action.response else None
                    target_player = get_player_by_number(players, target_id) if target_id else None
                    if target_player and not target_player['dead']:
                        target_player['protected'] = True
                        print(f" - Monk {player['name']} has protected {target_player['name']}.")
                    else:
                        print(f" - Monk {player['name']}'s target is invalid or already dead.")

                case "Fortune Teller":
                    # Fortune Teller investigates two players. This is informational
                    # only: attach a short reveal string to the Fortune Teller's
                    # player state so it can be presented to them next round.
                    targets = action.response or []
                    ft_player = player
                    if len(targets) < 2:
                        ft_player['info_for_player'] = "insufficient targets"
                        print(f" - Fortune Teller {player['name']} did not provide two targets.")
                        continue

                    t1 = get_player_by_number(players, targets[0])
                    t2 = get_player_by_number(players, targets[1])
                    if not t1 or not t2:
                        ft_player['info_for_player'] = "invalid target(s)"
                        print(f" - Fortune Teller {player['name']} targeted invalid player(s).")
                        continue

                    # For now, the simple rule: if either target is the Imp OR
                    # matches the Fortune Teller's configured `red_herring` id,
                    # the FT should be told that at least one is evil.
                    red_herring = ft_player.get('red_herring')
                    red_hit = False
                    if red_herring is not None:
                        red_hit = (targets[0] == red_herring) or (targets[1] == red_herring)

                    if t1.get('role') == 'Imp' or t2.get('role') == 'Imp' or red_hit:
                        ft_player['info_for_player'] = "at least one is evil"
                        print(f" - Fortune Teller {player['name']} learned at least one target is evil.")
                    else:
                        ft_player['info_for_player'] = "neither is evil"
                        print(f" - Fortune Teller {player['name']} learned neither target is evil.")

    return players
def get_player_by_number(players: list, number: int) -> Optional[Dict[str, Any]]:
    """Return the player dict whose 'id' matches number, or None if not found."""
    for player in players:
        if player.get("id") == number:
            return player
    return None

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Print a single clean line on Ctrl-C instead of a traceback
        print("Interrupted by user")
        sys.exit(1)