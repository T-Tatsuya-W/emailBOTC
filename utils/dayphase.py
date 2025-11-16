from __future__ import annotations

from typing import List, Dict, Any, Optional
import re
import time

from utils.message_handler import Message, MessageHandler
from utils.email_handler import EmailHandler
from utils.settings import DEFAULT_POLL_EVERY, DEFAULT_POLL_FOR


def get_day_nominations_first(players: List[Dict[str, Any]], *, day_number: int = 1) -> List[Message]:
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
        subject = f"day {day_number} nominations {player.get('name')} [{player.get('id')} ]"

        # Start with a public announcement about the previous night so the
        # players immediately see whether anyone died during the night.
        night_announce = player.get("last_night_announcement")
        if not night_announce:
            night_announce = "No player has died."

        # Build the list of players (alive/dead) after the announcement
        body_top = night_announce + "\n\nCurrent players:\n" + player_states

        # If this player learned information during the previous night, include
        # that info *before* the action prompt so the player sees it first.
        info_text = None
        if "info_for_player" in player and player.get("info_for_player") is not None:
            info_val = player.get("info_for_player")
            info_text = None
            # Support string messages (Investigator) first
            if isinstance(info_val, str):
                info_text = info_val
            elif isinstance(info_val, bool):
                # If we have metadata about what was attempted, include
                # that in the summary (e.g. "You tried to investigate
                # players X and Y, and learned that neither is evil").
                action = player.get("info_action")
                targets = player.get("info_targets") or []
                if action and targets:
                    # Build a readable target list with ids and names
                    pairs = []
                    for tid in targets:
                        t = next((pp for pp in players if pp.get("id") == tid), None)
                        if t:
                            pairs.append(f"{tid} ({t.get('name')})")
                        else:
                            pairs.append(str(tid))

                    if len(pairs) == 1:
                        tried = f"You tried to {action} player {pairs[0]}"
                    else:
                        tried = f"You tried to {action} players {pairs[0]} and {pairs[1]}"

                    if info_val is True:
                        info_text = f"{tried}, and learned that one of them is the demon."
                    else:
                        info_text = f"{tried}, and learned that neither is the demon."
                else:
                    # Fallback short messages
                    if info_val is True:
                        info_text = "You learned that at least one of your targets is evil."
                    else:
                        info_text = "You learned that neither of your targets is evil."

        # Compose the rest of the body depending on alive/dead status
        if player.get("dead"):
            body = (
                f"Hello {player['name']},\n" + body_top + "\n"
                "You are dead — no nomination available. \nReply to this email to acknowledge.\n"
            )
            expected = 0
        else:
            # Place any informative line before the action prompt
            prompt = (
                "To nominate a player reply with a single integer (player id). \nIf you do not wish to nominate, reply without a number to acknowledge.\n"
            )
            if info_text:
                body = f"Hello {player['name']},\n" + body_top + "\n\nNight information: " + info_text + "\n\n" + prompt
            else:
                body = f"Hello {player['name']},\n" + body_top + "\n" + prompt
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
        # Mark messages from the nomination step so the message handler
        # can treat them specially (e.g. return early when a nomination
        # integer is received).
        msg.is_nomination = True
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
    poll_every: Optional[int] = None,
    poll_for: Optional[int] = None,
    *,
    day_number: int = 1,
) -> List[Message]:
    """Construct, send and resolve day-phase nomination messages.

    Returns the list of resolved `Message` objects. This function is
    nomination-specific; voting logic can be implemented in a separate
    function later.
    """
    messages = get_day_nominations_first(players, day_number=day_number)
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
    # Use provided polling values or fall back to shared defaults
    poll_every = poll_every if poll_every is not None else DEFAULT_POLL_EVERY
    poll_for = poll_for if poll_for is not None else DEFAULT_POLL_FOR

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
    poll_every: Optional[int] = None,
    poll_for: Optional[int] = None,
    *,
    day_number: int = 1,
) -> List[Dict[str, Any]]:
    """Run the day phase: solicit optional nominations and print the result.

    Returns the (possibly modified) players list.
    """
    print("Starting day phase. Collecting nominations...")
    # Use provided polling values or fall back to shared defaults
    poll_every = poll_every if poll_every is not None else DEFAULT_POLL_EVERY
    poll_for = poll_for if poll_for is not None else DEFAULT_POLL_FOR

    # We'll allow multiple nomination->voting rounds within the day window.
    # Track which players have already nominated this day so they cannot
    # nominate again in subsequent rounds.
    start_time = time.time()
    end_time = start_time + poll_for

    has_nominated = set()
    leading_nom = None  # dict with keys 'id' and 'yes'
    tie = False

    # Precompute majority threshold (alive players at start of day)
    alive_count = sum(1 for p in players if not p.get("dead"))
    threshold = (alive_count + 1) // 2

    # Reuse the provided message_handler/email_handler or create defaults
    if email_handler is None:
        email_handler = EmailHandler()
    if message_handler is None:
        # We'll create per-round MessageHandler instances as needed
        message_handler = MessageHandler(email_handler, [], max_player_id=len(players))

    announcement_text = None

    # Loop until time runs out or all alive players have nominated
    while time.time() < end_time and len(has_nominated) < alive_count:
        remaining = max(0.0, end_time - time.time())

        # Build messages for players who haven't nominated and are alive
        round_players = [p for p in players if not p.get("dead") and p.get("id") not in has_nominated]
        if not round_players:
            break

        round_messages: List[Message] = []
        for player in round_players:
            # Build the same daytime message as the template function
            subject = f"day {day_number} nominations {player['name']} [{player.get('id')} ]"
            body = (
                f"Hello {player['name']},\nIt's day time! current players:\n"
                + "".join(f"- {p['id']}: {p['name']} (is {'dead' if p['dead'] else 'alive'})\n" for p in players)
                + "\nTo nominate a player reply with a single integer (player id). \nIf you do not wish to nominate, reply without a number to acknowledge.\n"
            )
            if "info_for_player" in player and player.get("info_for_player") is not None:
                info_val = player.get("info_for_player")
                info_text = None
                # Support string messages (Investigator) first
                if isinstance(info_val, str):
                    info_text = info_val
                elif isinstance(info_val, bool):
                    action = player.get("info_action")
                    targets = player.get("info_targets") or []
                    if action and targets:
                        pairs = []
                        for tid in targets:
                            t = next((pp for pp in players if pp.get("id") == tid), None)
                            if t:
                                pairs.append(f"{tid} ({t.get('name')})")
                            else:
                                pairs.append(str(tid))

                        if len(pairs) == 1:
                            tried = f"You tried to {action} player {pairs[0]}"
                        else:
                            tried = f"You tried to {action} players {pairs[0]} and {pairs[1]}"

                        if info_val is True:
                            info_text = f"{tried}, and learned that at least one is evil."
                        else:
                            info_text = f"{tried}, and learned that neither is evil."
                    else:
                        if info_val is True:
                            info_text = "You learned that at least one of your targets is evil."
                        else:
                            info_text = "You learned that neither of your targets is evil."

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
                expected_response_number=0,
                playerName=player.get("name", ""),
                canChooseSelf=True,
            )
            # Mark this round's message as a nomination prompt so the
            # MessageHandler can detect a nomination and return early.
            msg.is_nomination = True
            msg.is_dead = bool(player.get("dead", False))
            round_messages.append(msg)

        # Use a fresh MessageHandler for the round to avoid mixing state
        round_mh = MessageHandler(email_handler, round_messages, max_player_id=len(players))
        round_mh.allowed_nomination_ids = {p.get("id") for p in players if not p.get("dead")}

        # Ask for nominations and stop when a nomination is received or timeout
        round_responses = round_mh.send_and_resolve_all(round_messages, poll_every=poll_every, poll_for=remaining, stop_on_nomination=True)

        # Check if a nomination was made this round
        nomination = select_nomination_from_messages(round_responses, players)
        if nomination is None:
            # no nomination this round; continue to remaining time
            continue

        print(f"Nomination received: player {nomination}")

        # Identify which player made the nomination (the message whose response contains it)
        nominator_id = None
        for m in round_responses:
            for n in getattr(m, "response", []) or []:
                if isinstance(n, int) and n == nomination:
                    nominator_id = m.playernumber
                    break
            if nominator_id is not None:
                break

        if nominator_id is not None:
            has_nominated.add(nominator_id)

        # Conduct voting on the nominated player (use remaining time)
        remaining_after_nom = max(0.0, end_time - time.time())
        votes = get_day_voting(
            players,
            nomination,
            message_handler=message_handler,
            email_handler=email_handler,
            poll_every=poll_every,
            poll_for=remaining_after_nom,
            leading_nom=leading_nom,
            threshold=threshold,
        )

        # Tally yes votes for this round
        yes_count = 0
        for vote in votes:
            v = (vote or "").casefold()
            if re.search(r"\b(yes|yeah|ye|y|aye|yea|approve|accept)\b", v, flags=re.IGNORECASE):
                yes_count += 1

        print(f"Round yes votes: {yes_count}")

        # Only nominations that reach the majority threshold are eligible to be leading
        if yes_count >= threshold:
            if leading_nom is None:
                leading_nom = {"id": nomination, "yes": yes_count}
                tie = False
            else:
                if yes_count > leading_nom["yes"]:
                    leading_nom = {"id": nomination, "yes": yes_count}
                    tie = False
                elif yes_count == leading_nom["yes"]:
                    # exact tie -> neither will be killed
                    leading_nom = None
                    tie = True

        # continue loop to allow further nominations until time expires

    # After nomination rounds complete, apply final outcome
    if leading_nom and not tie and leading_nom.get("yes", 0) >= threshold:
        target = next((p for p in players if p.get("id") == leading_nom["id"]), None)
        if target and not target.get("dead"):
            target["dead"] = True
            announcement_text = f"Player {leading_nom['id']} ({target.get('name')}) was lynched by vote."
            print(announcement_text)
        else:
            announcement_text = "Nomination passed but target was invalid or already dead."
    else:
        if tie:
            announcement_text = "Tie between top nominees; no lynch." 
            print(announcement_text)
        else:
            announcement_text = "No majority reached during the day; no lynch."
            print(announcement_text)

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
    poll_every: Optional[int] = None,
    poll_for: Optional[int] = None,
    *,
    leading_nom: Optional[Dict[str, Any]] = None,
    threshold: Optional[int] = None,
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

            # If there is a current leading nomination from earlier rounds,
            # inform voters which player is currently set to be lynched and how
            # many yes votes are required to match or beat them.
            if leading_nom and threshold is not None:
                try:
                    lead_id = leading_nom.get("id")
                    lead_yes = int(leading_nom.get("yes", 0))
                    lead_player = next((p for p in players if p.get("id") == lead_id), None)
                    lead_name = lead_player.get("name") if lead_player else str(lead_id)
                    # To match the current leading nominee a challenger needs
                    # `lead_yes` yes votes; to beat them they need `lead_yes + 1`.
                    body += (
                        f"\n\nCurrent leading nominee: {lead_name} (player {lead_id}) with {lead_yes} yes votes. "
                        f"To match them this nomination needs {lead_yes} yes votes; to beat them it needs {lead_yes + 1} yes votes.\n"
                    )
                except Exception:
                    # Defensive: ignore formatting errors and fall back to
                    # the simple message body.
                    pass

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
    # Use provided polling values or fall back to shared defaults
    poll_every = poll_every if poll_every is not None else DEFAULT_POLL_EVERY
    poll_for = poll_for if poll_for is not None else DEFAULT_POLL_FOR

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
