from __future__ import annotations

from typing import Optional, Dict, Any, List

from utils.email_handler import EmailHandler
from utils.message_handler import Message, MessageHandler
from utils.settings import DEFAULT_POLL_EVERY, DEFAULT_POLL_FOR


def nightphase(
    players: list,
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
) -> list:
    """Run a simplified night phase (moved out of `main.py`).

    This function accepts optional handler parameters so tests can inject
    mocks. It builds the messages, collects responses and applies role
    resolution logic via helpers in this module.
    """

    print("Starting night phase with players:")

    player_states = ""
    for player in players:
        player_states += f"- {player['id']}: {player['name']} (is {'dead' if player['dead'] else 'alive'})\n"

    print(player_states)

    actions = get_night_actions(players, message_handler=message_handler, email_handler=email_handler)
    return perform_night_actions(players, actions)


def get_night_actions(
    players: list,
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
    poll_every: Optional[int] = None,
    poll_for: Optional[int] = None,
) -> List[Message]:
    """Construct night prompts, send them and collect resolved actions."""

    messages: list[Message] = []
    player_states = ""
    for player in players:
        player_states += f"- {player['id']}: {player['name']} (is {'dead' if player['dead'] else 'alive'})\n"

    for player in players:
        subject = f"Night Phase Actions {player['name']}"
        # Build a role-aware body. Dead players do not perform actions;
        # explain that they are dead and may optionally acknowledge the update.
        if player.get("dead"):
            body = (
                f"Hello {player['name']},\nIt's night time! current players:\n{player_states}\n"
                "You are dead — no night action is available.\n"
                "(you must reply to acknowledge this message)."
            )
        else:
            expected = player.get("nightResponse", 0)
            if expected == 0:
                body = (
                    f"Hello {player['name']},\nIt's night time! current players:\n{player_states}\n"
                    f"As a [{player['role']}], you have no night action to perform tonight.\n"
                    "(you must reply to acknowledge this message)."
                )
            else:
                body = (
                    f"Hello {player['name']},\nIt's night time! current players:\n{player_states}\n"
                    f"As a [{player['role']}], you need to respond with {expected} integer(s)."
                )
        expected = 0 if player.get("dead") else player.get("nightResponse", 0)

        # If there is a day announcement (e.g. lynch result) include it in the
        # night-time email so players are informed of what happened today.
        last_day = player.get("last_day_announcement")
        if last_day:
            body = last_day + "\n\n" + body

        message = Message(
            priority=player['nightActionPriority'],
            address=player['email'],
            subject=subject,
            body=body,
            resolved=False,
            response=[],
            playernumber=player["id"],
            responseBody="",
            expected_response_number=expected,
            playerName=player["name"],
            canChooseSelf=player["canChooseSelf"],
        )
        messages.append(message)

    if email_handler is None:
        email_handler = EmailHandler()

    if message_handler is None:
        message_handler = MessageHandler(email_handler, messages, max_player_id=len(players))
    else:
        message_handler.messages = messages
        message_handler.max_player_id = len(players)

    # Use provided polling values or fall back to shared defaults
    poll_every = poll_every if poll_every is not None else DEFAULT_POLL_EVERY
    poll_for = poll_for if poll_for is not None else DEFAULT_POLL_FOR

    responses = message_handler.send_and_resolve_all(messages, poll_every=poll_every, poll_for=poll_for)
    return responses


def perform_night_actions(players: list, responses: list[Message]) -> list:
    """Apply actions (responses) to the players list according to priority."""
    for priority in range(1, 5):
        for action in [a for a in responses if getattr(a, "priority", None) == priority]:
            player = get_player_by_number(players, action.playernumber)
            print(f"Processing actions for Player {action.playernumber} ({player['name']}): {action.response}")
            match player['role']:
                case "Imp":
                    target_id = action.response[0] if action.response else None
                    target_player = get_player_by_number(players, target_id) if target_id else None
                    if target_player and not target_player['dead']:
                        if target_player.get('protected'):
                            print(f" - Imp {player['name']}'s target {target_player['name']} was protected; kill prevented.")
                        else:
                            target_player['dead'] = True
                            print(f" - Imp {player['name']} has killed {target_player['name']}.")
                    else:
                        print(f" - Imp {player['name']}'s target is invalid or already dead.")

                case "Poisoner":
                    for p in players:
                        p['poisoned'] = False

                    target_id = action.response[0] if action.response else None
                    target_player = get_player_by_number(players, target_id) if target_id else None
                    if target_player and not target_player['dead']:
                        target_player['poisoned'] = True
                        # Poisoning removes any existing protection (including the
                        # Soldier's default protection) so the target becomes
                        # vulnerable to subsequent kills unless re-protected.
                        target_player['protected'] = False
                        print(f" - Poisoner {player['name']} has poisoned {target_player['name']}.")
                    else:
                        print(f" - Poisoner {player['name']}'s target is invalid or already dead.")

                case "Monk":
                    # Reset protection for non-Soldier players; Soldiers retain
                    # their default protection state unless explicitly poisoned.
                    for p in players:
                        if p.get('role') != 'Soldier':
                            p['protected'] = False

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
                    targets = action.response or []
                    ft_player = player
                    if len(targets) < 2:
                        ft_player['info_for_player'] = None
                        print(f" - Fortune Teller {player['name']} did not provide two targets.")
                        continue

                    t1 = get_player_by_number(players, targets[0])
                    t2 = get_player_by_number(players, targets[1])
                    if not t1 or not t2:
                        ft_player['info_for_player'] = None
                        print(f" - Fortune Teller {player['name']} targeted invalid player(s).")
                        continue

                    red_herring = ft_player.get('red_herring')
                    red_hit = False
                    if red_herring is not None:
                        red_hit = (targets[0] == red_herring) or (targets[1] == red_herring)

                    imp_hit = t1.get('role') == 'Imp' or t2.get('role') == 'Imp'
                    info_result = imp_hit or red_hit

                    if ft_player.get('poisoned'):
                        info_result = not info_result

                    ft_player['info_for_player'] = info_result

                    if info_result:
                        print(f" - Fortune Teller {player['name']} learned at least one target is evil.")
                    else:
                        print(f" - Fortune Teller {player['name']} learned neither target is evil.")

    return players


def get_player_by_number(players: list, number: int) -> Optional[Dict[str, Any]]:
    for player in players:
        if player.get("id") == number:
            return player
    return None
