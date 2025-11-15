from __future__ import annotations

from typing import List, Dict, Any, Optional

from utils.message_handler import Message, MessageHandler
from utils.email_handler import EmailHandler


def get_day_messages(players: List[Dict[str, Any]]) -> List[Message]:
    """Construct message templates for the day phase without sending.

    This returns a list of `Message` objects suitable for use with
    `MessageHandler.send_and_resolve_all` in tests.
    """
    player_states = ""
    for p in players:
        player_states += f"- {p['id']}: {p['name']} (is {'dead' if p['dead'] else 'alive'})\n"

    messages: List[Message] = []
    for player in players:
        subject = f"Day Phase Nominations {player['name']}"
        # All players receive the prompt but dead players are informed
        # and are not expected to reply. Alive players may optionally
        # nominate by replying with a single integer.
        if player.get("dead"):
            body = (
                f"Hello {player['name']},\nIt's day time! current players:\n{player_states}\n"
                "You are dead — no nomination available. \nReply to this email to acknowledge.\n"
            )
            expected = 0
        else:
            body = (
                f"Hello {player['name']},\nIt's day time! current players:\n{player_states}\n"
                "To nominate a player reply with a single integer (player id). \nIf you do not wish to nominate, reply without a number to acknowledge.\n"
            )
            expected = 0

        msg = Message(
            priority=4,
            address=player.get("email") or "",
            subject=subject,
            body=body,
            resolved=False,
            response=[],
            playernumber=player.get("id", 0),
            responseBody="",
            expected_response_number=expected,
            playerName=player.get("name", ""),
            canChooseSelf=True,
        )
        # mark if the player is dead so handlers can ignore invalid noms
        msg.is_dead = bool(player.get("dead", False))
        messages.append(msg)

    return messages


def select_nomination_from_messages(messages: List[Message], players: List[Dict[str, Any]]) -> Optional[int]:
    """Return the first valid nomination integer found in messages responses.

    The first integer across messages (in list order) that refers to a valid
    alive player id is returned. If none found, return None.
    """
    max_id = max((p.get("id", 0) for p in players), default=0)
    alive_ids = {p.get("id") for p in players if not p.get("dead")}

    # Consider only messages that have recorded responses. Use the recorded
    # response timestamp `_response_time` to pick the earliest arrived nomination.
    candidates = []
    for msg in messages:
        resp = getattr(msg, "response", []) or []
        if not resp:
            continue
        # Only consider messages that recorded a response time
        resp_time = getattr(msg, "_response_time", None)
        if resp_time is None:
            # If no timestamp, treat as later-than-any; still include with large key
            resp_time = float("inf")
        candidates.append((resp_time, msg))

    if not candidates:
        return None

    # Pick the message with the smallest response time
    candidates.sort(key=lambda x: x[0])
    for _, msg in candidates:
        for n in getattr(msg, "response", []) or []:
            if isinstance(n, int) and 1 <= n <= max_id and n in alive_ids:
                return n

    return None


def get_day_actions(
    players: List[Dict[str, Any]],
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
    poll_every: int = 1,
    poll_for: int = 1,
) -> List[Message]:
    """Construct, send and resolve day-phase messages.

    Returns the list of resolved `Message` objects.
    """
    messages = get_day_messages(players)
    if email_handler is None:
        email_handler = EmailHandler()

    # compute alive ids so the message handler can validate nominations
    alive_ids = {p.get("id") for p in players if not p.get("dead")}

    if message_handler is None:
        message_handler = MessageHandler(email_handler, messages, max_player_id=len(players))
    else:
        message_handler.messages = messages
        message_handler.max_player_id = len(players)

    # provide allowed nomination ids to the handler so it can reject invalid noms
    message_handler.allowed_nomination_ids = alive_ids

    # Stop as soon as any nomination is received (an optional integer in a
    # zero-expected message) or until all messages are resolved with no noms.
    responses = message_handler.send_and_resolve_all(
        messages, poll_every=poll_every, poll_for=poll_for, stop_on_nomination=True
    )
    return responses


def dayphase(
    players: List[Dict[str, Any]],
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
    poll_every: int = 1,
    poll_for: int = 1,
) -> List[Dict[str, Any]]:
    """Run the day phase: solicit optional nominations and print the result.

    Returns the (possibly modified) players list.
    """
    print("Starting day phase. Collecting nominations...")
    responses = get_day_actions(players, message_handler=message_handler, email_handler=email_handler, poll_every=poll_every, poll_for=poll_for)

    nomination = select_nomination_from_messages(responses, players)
    if nomination is None:
        print("No nomination was made this day.")
    else:
        print(f"Nomination received: player {nomination}")

    return players
