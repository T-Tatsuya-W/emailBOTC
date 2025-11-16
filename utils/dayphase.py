from __future__ import annotations

from typing import List, Dict, Any, Optional
import re

from utils.message_handler import Message, MessageHandler
from utils.email_handler import EmailHandler


def get_day_nominations_first(players: List[Dict[str, Any]]) -> List[Message]:
    """Construct message templates for the day-phase nominations step.

    This returns a list of `Message` objects suitable for use with
    `MessageHandler.send_and_resolve_all`. The function name emphasises
    that this step solicits nominations first; voting/other day steps
    can be implemented in separate functions later.
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

        # If this player learned information during the previous night, include it
        # in the daytime nomination message so they see their investigative result.
        if "info_for_player" in player and player.get("info_for_player") is not None:
            info_val = player.get("info_for_player")
            if info_val is True:
                info_text = "You learned that at least one of your targets is evil."
            elif info_val is False:
                info_text = "You learned that neither of your targets is evil."
            else:
                info_text = None

            if info_text:
                body += "\n\nNight information: " + info_text

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

# Backwards compatibility: keep the old name available for tests and callers
get_day_messages = get_day_nominations_first


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


def get_day_nominations_actions(
    players: List[Dict[str, Any]],
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
    poll_every: int = 1,
    poll_for: int = 1,
) -> List[Message]:
    """Construct, send and resolve day-phase nomination messages.

    Returns the list of resolved `Message` objects. This function is
    nomination-specific; voting logic can be implemented in a separate
    function later.
    """
    messages = get_day_nominations_first(players)
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

# Backwards compatibility: keep the previous name available
get_day_actions = get_day_nominations_actions


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
    responses = get_day_nominations_actions(players, message_handler=message_handler, email_handler=email_handler, poll_every=poll_every, poll_for=poll_for)

    nomination = select_nomination_from_messages(responses, players)
    announcement_text = None
    if nomination is None:
        print("No nomination was made this day.")
        announcement_text = "No nomination was made today."
    else:
        print(f"Nomination received: player {nomination}")

        # Conduct voting on the nominated player
        votes = get_day_voting(players, nomination, message_handler=message_handler, email_handler=email_handler, poll_every=poll_every, poll_for=poll_for)
        # Tally votes
        tally = {"yes": 0, "no": 0, "abstain": 0, "no_response": 0}
        for vote in votes:
            v = (vote or "").casefold()
            if re.search(r"\b(abs|abstain|abstention)\b", v, flags=re.IGNORECASE):
                tally["abstain"] += 1
            elif re.search(r"\b(yes|y|aye|yea|approve|accept)\b", v, flags=re.IGNORECASE):
                tally["yes"] += 1
            elif re.search(r"\b(no|n|nay|reject|deny)\b", v, flags=re.IGNORECASE):
                tally["no"] += 1
            elif v.strip() == "":
                tally["no_response"] += 1
            else:
                # Unrecognised responses count as abstain
                tally["abstain"] += 1

        print("Voting results:")
        print(f" - Yes: {tally['yes']}")
        print(f" - No: {tally['no']}")
        print(f" - Abstain: {tally['abstain']}")
        print(f" - No response: {tally['no_response']}")

        # Determine majority threshold among alive players. A nomination is
        # executed (player is killed) if number of 'yes' votes is >= ceil(alive/2).
        alive_count = sum(1 for p in players if not p.get("dead"))
        # majority threshold (round up)
        threshold = (alive_count + 1) // 2
        if tally["yes"] >= threshold:
            target = next((p for p in players if p.get("id") == nomination), None)
            if target and not target.get("dead"):
                target["dead"] = True
                print(f"Nomination passed: player {nomination} ({target.get('name')}) has been lynched by vote.")
                announcement_text = f"Player {nomination} ({target.get('name')}) was lynched by vote."
            else:
                print("Nomination passed but target invalid or already dead.")
                announcement_text = "Nomination passed but target was invalid or already dead."
        else:
            print(f"No majority: {tally['yes']}/{threshold} yes votes; nomination fails.")
            announcement_text = f"No majority: {tally['yes']}/{threshold} yes votes; nomination failed."

    # Attach the announcement text so the subsequent night messages can include
    # the day's result; this will be read by `get_night_actions` when composing
    # night-time emails.
    if announcement_text is not None:
        for p in players:
            p["last_day_announcement"] = announcement_text

    return players


def get_day_voting(
    players: List[Dict[str, Any]],
    nominated_id: int,
    message_handler: Optional[MessageHandler] = None,
    email_handler: Optional[EmailHandler] = None,
    poll_every: int = 1,
    poll_for: int = 60,
) -> List[Optional[str]]:
    """Announce the nomination and collect votes from all players.

    Returns a list of `responseBody` strings (one per message/player) in the
    same order as `players`.
    """
    # Find nominated player's name for the message
    nominated_player = next((p for p in players if p.get("id") == nominated_id), None)
    nominated_name = nominated_player.get("name") if nominated_player else str(nominated_id)

    messages: List[Message] = []
    # Keep track of which players we create messages for so we can map
    # collected responses back into the original players order. Dead
    # players are eligible only if they still have a ghost vote available
    # (player.get('canVote', True) is True) — `canVote` is provided by
    # the player factory so use that key consistently.
    eligible_indices: List[int] = []
    for idx, player in enumerate(players):
        is_dead = bool(player.get("dead", False))
        canvote = player.get("canVote", True)
        # Alive players always get to vote; dead players only if canVote is True
        if not is_dead or (is_dead and canvote):
            subject = f"Day Vote: Nomination for {nominated_name}"
            body = (
                f"Hello {player.get('name')},\nA nomination has been made for {nominated_name} (player {nominated_id}).\n"
                "Please reply with 'YES' to vote in favour, 'NO' to vote against, or 'ABS' to abstain."
            )

            msg = Message(
                priority=4,
                address=player.get("email") or "",
                subject=subject,
                body=body,
                resolved=False,
                response=[],
                playernumber=player.get("id", 0),
                responseBody="",
                expected_response_number=0,
                playerName=player.get("name", ""),
                canChooseSelf=True,
            )
            msg.is_dead = is_dead
            messages.append(msg)
            eligible_indices.append(idx)

    if email_handler is None:
        email_handler = EmailHandler()

    if message_handler is None:
        message_handler = MessageHandler(email_handler, messages, max_player_id=len(players))
    else:
        message_handler.messages = messages
        message_handler.max_player_id = len(players)

    # Send vote requests and collect free-text responses in `responseBody`.
    responses = message_handler.send_and_resolve_all(messages, poll_every=poll_every, poll_for=poll_for)

    # Map responses back to players order. For players who were not eligible
    # to vote this round (dead and already used their ghost vote), return
    # an empty string. If a dead player did vote (non-empty response), set
    # their `canvote` flag to False so they can't vote again.
    votes_by_player: List[Optional[str]] = []
    resp_iter = iter(responses)
    for idx, player in enumerate(players):
        if idx in eligible_indices:
            # responses are in the same order as messages created
            m = next(resp_iter)
            resp_body = getattr(m, "responseBody", "") or ""
            # If this was a dead player and they provided a non-empty vote,
            # consume their one ghost vote by clearing the `canVote` flag
            # that comes from the player factory.
            if player.get("dead") and resp_body.strip():
                player["canVote"] = False
            votes_by_player.append(resp_body)
        else:
            votes_by_player.append("")

    return votes_by_player
