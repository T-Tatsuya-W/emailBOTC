from __future__ import annotations

from typing import Optional, Dict, Any, List

from utils.email_handler import EmailHandler
from utils.message_handler import Message, MessageHandler
from utils.settings import DEFAULT_POLL_EVERY, DEFAULT_POLL_FOR


def nightphase(
    players: list,
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
    *,
    night_number: int = 1,
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

    actions = get_night_actions(players, message_handler=message_handler, email_handler=email_handler, first_night=False, night_number=night_number)
    return perform_night_actions(players, actions)


def first_nightphase(
    players: List[dict],
    message_handler: Optional[MessageHandler] = None,
    poll_every: Optional[int] = None,
    poll_for: Optional[int] = None,
    email_handler: Optional[EmailHandler] = None,
) -> List[dict]:
    """Run the special first night phase.

    For now this mirrors the normal `nightphase` behavior but emits
    distinguishing prints so callers and logs can observe "first night"
    behavior. In future we can branch role handling here (some roles
    only act on the first night, others are disabled on the first night).
    """
    print("--- Starting FIRST night phase ---")
    # include a brief per-player print to help with debugging and tests
    for p in players:
        print(f"First night: player {p.get('name', p.get('email'))} (alive={p.get('alive', True)})")

    # Construct and resolve actions with first_night=True so role logic can
    # decide whether to be active on night 1.
    responses = get_night_actions(
        players,
        message_handler=message_handler,
        email_handler=email_handler,
        poll_every=poll_every,
        poll_for=poll_for,
        first_night=True,
        night_number=1,
    )
    updated_players = perform_night_actions(players, responses)

    print("--- Finished FIRST night phase ---")
    return updated_players


def get_night_actions(
    players: list,
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
    poll_every: Optional[int] = None,
    poll_for: Optional[int] = None,
    first_night: bool = False,
    *,
    night_number: int = 1,
) -> List[Message]:
    """Construct night prompts, send them and collect resolved actions."""

    messages: list[Message] = []
    player_states = ""
    for player in players:
        player_states += f"- {player['id']}: {player['name']} (is {'dead' if player['dead'] else 'alive'})\n"

    for player in players:
        subject = f"night {night_number} actions {player['name']} [{player.get('id')}]"
        # Build a role-aware body. Dead players do not perform actions;
        # explain that they are dead and may optionally acknowledge the update.
        if player.get("dead"):
            body = (
                f"Hello {player['name']},\nIt's night time! current players:\n{player_states}\n"
                "You are dead — no night action is available.\n"
                "(you must reply to acknowledge this message)."
            )
            expected = 0
        else:
            # Allow roles/players to control whether they act on the first
            # night using per-player flags. This keeps the function generic
            # while allowing role implementations to set these flags when a
            # player is created (see `player_factory`).
            if player.get("first_night_only") and not first_night:
                expected = 0
                body = (
                    f"Hello {player['name']},\nIt's night time! current players:\n{player_states}\n"
                    f"As a [{player['role']}], you only act on the first night — no action tonight.\n"
                    "(you must reply to acknowledge this message)."
                )
            elif player.get("skip_first_night") and first_night:
                expected = 0
                body = (
                    f"Hello {player['name']},\nIt's night time! current players:\n{player_states}\n"
                    f"As a [{player['role']}], you do not act on the first night — no action tonight.\n"
                    "(you must reply to acknowledge this message)."
                )
            else:
                expected = player.get("nightResponse", 0)
                if expected == 0:
                    # Special-case Investigator messaging on the first night:
                    # Investigators do not submit targets but they DO receive
                    # a result after all night actions resolve. Make the
                    # message explicit so players are not misled into
                    # thinking they have no role this night.
                    if first_night and player.get("role") == "Investigator":
                        body = (
                            f"Hello {player['name']},\nIt's night time! current players:\n{player_states}\n"
                            f"As an [{player['role']}], you will receive investigative information after all night actions have been processed. (you must reply to acknowledge this message).\n"
                        )
                    else:
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
    # Track which players were killed during this night so we can inform
    # the group at the start of the following day.
    killed_this_night: list[dict] = []

    # Add a visual blank line before the concise night-action log block
    # so it's easier to spot in console output.
    print("\n--- Night actions ---")

    for priority in range(1, 5):
        for action in [a for a in responses if getattr(a, "priority", None) == priority]:
            player = get_player_by_number(players, action.playernumber)
            # Prepare concise one-line log descriptions for each player action
            role = player.get('role')
            action_response = action.response or []

            if role == "Imp":
                target_id = action_response[0] if action_response else None
                target_player = get_player_by_number(players, target_id) if target_id else None
                prior_status = "healthy"
                if target_player:
                    if target_player.get('poisoned'):
                        prior_status = "poisoned"
                    elif target_player.get('drunk'):
                        prior_status = "drunk"

                if target_player and not target_player['dead']:
                    if target_player.get('protected'):
                        outcome = "fails"
                        suffix = "(protected)"
                    else:
                        outcome = "succeeds"
                        target_player['dead'] = True
                        killed_this_night.append(target_player)
                        suffix = f"(dead, {prior_status})"
                else:
                    outcome = "fails"
                    suffix = "(invalid or already dead)"

                print(f"player [{player.get('id')}] [Imp] tries to kill player(s) [{target_id}] and {outcome} {suffix}")

            elif role == "Poisoner":
                # clear prior poison marks
                for p in players:
                    p['poisoned'] = False

                target_id = action_response[0] if action_response else None
                target_player = get_player_by_number(players, target_id) if target_id else None
                if target_player and not target_player['dead']:
                    target_player['poisoned'] = True
                    target_player['protected'] = False
                    print(f"player [{player.get('id')}] [Poisoner] poisons player [{target_id}] ({target_player.get('name')})")
                else:
                    print(f"player [{player.get('id')}] [Poisoner] attempts to poison invalid or already-dead player [{target_id}]")

            elif role == "Monk":
                # Reset protection for non-Soldier players; Soldiers retain default
                for p in players:
                    if p.get('role') != 'Soldier':
                        p['protected'] = False

                if player.get('poisoned'):
                    print(f"player [{player.get('id')}] [Monk] tries to protect but fails (poisoned)")
                    continue

                target_id = action_response[0] if action_response else None
                target_player = get_player_by_number(players, target_id) if target_id else None
                if target_player and not target_player['dead']:
                    target_player['protected'] = True
                    print(f"player [{player.get('id')}] [Monk] tries to protect player(s) [{target_id}] and succeeds (protected)")
                else:
                    print(f"player [{player.get('id')}] [Monk] tries to protect player(s) [{target_id}] and fails (invalid or already dead)")

            elif role == "Fortune Teller":
                targets = action_response or []
                ft_player = player
                if len(targets) < 2:
                    ft_player['info_for_player'] = None
                    print(f"player [{player.get('id')}] [Fortune Teller] tries to investigate players {targets} and fails (insufficient targets)")
                    continue

                t1 = get_player_by_number(players, targets[0])
                t2 = get_player_by_number(players, targets[1])
                if not t1 or not t2:
                    ft_player['info_for_player'] = None
                    print(f"player [{player.get('id')}] [Fortune Teller] tries to investigate players {targets} and fails (invalid targets)")
                    continue

                red_herring = ft_player.get('red_herring')
                red_hit = False
                if red_herring is not None:
                    red_hit = (targets[0] == red_herring) or (targets[1] == red_herring)

                imp_hit = t1.get('role') == 'Imp' or t2.get('role') == 'Imp'
                info_result = imp_hit or red_hit

                poisoned_flag = bool(ft_player.get('poisoned'))
                if poisoned_flag:
                    info_result = not info_result

                # Record both the boolean result and metadata about the
                # inquiry so the daytime message can include a readable
                # summary (what they tried to do and which targets).
                ft_player['info_for_player'] = info_result
                ft_player['info_targets'] = targets
                ft_player['info_action'] = 'investigate'
                if poisoned_flag:
                    print(f"player [{player.get('id')}] [Fortune Teller] investigates players [{targets[0]} {targets[1]}] and learns {info_result} (poisoned - inverted)")
                else:
                    print(f"player [{player.get('id')}] [Fortune Teller] investigates players [{targets[0]} {targets[1]}] and learns {info_result}")

            elif role == "Investigator":
                inv_player = player
                import random

                # If the Investigator is poisoned, they get noisy results:
                # pick two random other players (not self).
                if inv_player.get('poisoned'):
                    others = [p.get('id') for p in players if p.get('id') != inv_player.get('id')]
                    suspects = random.sample(others, min(2, len(others))) if others else []
                else:
                    poisoner_ids = [p.get('id') for p in players if p.get('role') == 'Poisoner' and not p.get('dead')]
                    if poisoner_ids:
                        p_id = random.choice(poisoner_ids)
                        others = [p.get('id') for p in players if p.get('id') != inv_player.get('id') and p.get('id') != p_id]
                        if others:
                            suspects = [p_id, random.choice(others)]
                        else:
                            suspects = [p_id]
                    else:
                        others = [p.get('id') for p in players if p.get('id') != inv_player.get('id')]
                        suspects = random.sample(others, min(2, len(others))) if others else []

                if suspects:
                    pairs = []
                    for sid in suspects:
                        p = get_player_by_number(players, sid)
                        if p:
                            pairs.append(f"{sid} ({p.get('name')})")
                        else:
                            pairs.append(str(sid))
                    if len(pairs) == 1:
                        msg = f"Investigation: player {pairs[0]} is the Poisoner."
                    else:
                        msg = f"Investigation: one of {pairs[0]} or {pairs[1]} is the Poisoner."
                else:
                    msg = "Investigation: no suspects could be determined."

                inv_player['info_for_player'] = msg
                # Record metadata consistent with Fortune Teller so the
                # daytime formatter can build a readable sentence.
                inv_player['info_targets'] = suspects
                inv_player['info_action'] = 'investigate'
                if inv_player.get('poisoned'):
                    print(f"player [{player.get('id')}] [Investigator] receives info: {msg} (poisoned)")
                else:
                    print(f"player [{player.get('id')}] [Investigator] receives info: {msg}")

    # Compose a human-friendly night announcement and attach it to all
    # player records so the daytime messages can show what happened.
    if not killed_this_night:
        announcement = "No player has died."
    else:
        parts = [f"{p.get('id')} ({p.get('name')})" for p in killed_this_night]
        if len(parts) == 1:
            announcement = f"In the night player {parts[0]} has died."
        else:
            announcement = f"In the night players {', '.join(parts[:-1])} and {parts[-1]} have died."

    for p in players:
        p['last_night_announcement'] = announcement

    return players


def get_player_by_number(players: list, number: int) -> Optional[Dict[str, Any]]:
    for player in players:
        if player.get("id") == number:
            return player
    return None

