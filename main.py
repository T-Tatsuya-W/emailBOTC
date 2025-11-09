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
    
    players = [{
        "id": 1,
        "email": default_email,
        "name": "impPlayer",
        "alignment": "Evil",
        "role": "Imp",
        "drunk": False,
        "poisoned": False,
        "dead": False,
        "canVote": True,
        "protected": False,
        "nightResponse": 1,
        "canChooseSelf": True,
        "nightActionPriority": 3
    }, {
        "id": 2,
        "email": default_email,
        "name": "poisonerPlayer",
        "alignment": "Evil",
        "role": "Poisoner",
        "drunk": False,     
        "poisoned": False,
        "dead": False,
        "canVote": True,
        "protected": False,
        "nightResponse": 1,
        "canChooseSelf": False,
        "nightActionPriority": 1
    }, {
        "id": 3,
        "email": default_email,
        "name": "monkPlayer",
        "alignment": "Good",
        "role": "Monk",
        "drunk": False,     
        "poisoned": False,
        "dead": False,
        "canVote": True,
        "protected": False,
        "nightResponse": 1,
        "canChooseSelf": False,
        "nightActionPriority": 2
    }, {
        "id": 4,
        "email": default_email,
        "name": "fortuneTellerPlayer",
        "alignment": "Good",
        "role": "Fortune Teller",
        "drunk": False,
        "poisoned": False,
        "dead": False,
        "canVote": True,
        "protected": False,
        "nightResponse": 2,
        "canChooseSelf": False,
        "nightActionPriority": 4
    }, {
        "id": 5,
        "email": default_email,
        "name": "washerwomanPlayer",
        "alignment": "Good",
        "role": "Washerwoman",
        "drunk": False,
        "poisoned": False,
        "dead": False,
        "canVote": True,
        "protected": False,
        "nightResponse": 0,
        "canChooseSelf": True,
        "nightActionPriority": 4
    }]


    
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

    # Build messages for each player
    messages: list[Message] = []
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

    responses = message_handler.send_and_resolve_all(messages, poll_every=1, poll_for=1000)

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
                        target_player['dead'] = True
                        print(f" - Imp {player['name']} has killed {target_player['name']}.")
                    else:
                        print(f" - Imp {player['name']}'s target is invalid or already dead.")
                    if target_player and target_player['id'] == player['id']:
                        evil_players = [p for p in players if p['alignment'] == 'Evil' and not p['dead'] and p['id'] != player['id']]
                        if evil_players:
                            new_imp = evil_players[0]
                            new_imp['role'] = 'Imp'
                            print(f"   - {new_imp['name']} has become the new Imp.")

                case "Poisoner":
                    for p in players:
                        p['poisoned'] = False

                    target_id = action.response[0] if action.response else None
                    target_player = get_player_by_number(players, target_id) if target_id else None
                    if target_player and not target_player['dead']:
                        target_player['dead'] = True
                        target_player['poisoned'] = True
                        print(f" - Poisoner {player['name']} has poisoned {target_player['name']}.")
                    else:
                        print(f" - Poisoner {player['name']}'s target is invalid or already dead.")

                case "Monk":
                    for p in players:
                        p['protected'] = False
                        if p['role'] == 'Soldier':
                            p['protected'] = True

                    target_id = action.response[0] if action.response else None
                    target_player = get_player_by_number(players, target_id) if target_id else None
                    if target_player and not target_player['dead']:
                        target_player['protected'] = True
                        print(f" - Monk {player['name']} has protected {target_player['name']}.")
                    else:
                        print(f" - Monk {player['name']}'s target is invalid or already dead.")

                case "Fortune Teller":
                    pass

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