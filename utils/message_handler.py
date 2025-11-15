"""Message handling utilities.

Defines a simple Message dataclass and a MessageHandler which will orchestrate
operations involving an EmailHandler (real or mock). For now the handler only
stores an example message list to be used by unit tests while we build
functionality incrementally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import time
import re


@dataclass
class Message:
    """Represents a message to be handled.

    Fields required by the user request:
    - priority: int (1,2,3)
    - resolved: bool
    - response: list of up to 2 integers (not enforced here)
    - address: str
    - subject: str
    - body: str
    - playernumber: int
    - responseBody: str
    - expected_response_number: int (0, 1 or 2)
    """

    priority: int
    resolved: bool = False
    response: List[int] = field(default_factory=list)
    address: str = ""
    subject: str = ""
    body: str = ""
    playernumber: int = 0
    responseBody: str = ""
    # number of expected integer responses (0, 1 or 2)
    expected_response_number: int = 0
    playerName: str = ""
    canChooseSelf: bool = False


class MessageHandler:
    """Handles a list of Message objects and delegates email operations.

    The handler accepts an `email_handler` argument to allow swapping the
    real `EmailHandler` for `MockEmailHandler` in tests.
    """

    def __init__(
        self,
        email_handler: Optional[object] = None,
        messages: Optional[List[Message]] = None,
        max_player_id: int = 0,
    ) -> None:
        # store the provided email handler (real or mock) for future use
        self.email_handler = email_handler

        # Allow the caller to provide the initial list of Message objects.
        # If none are provided, start with an empty list.
        self.messages: List[Message] = list(messages) if messages else []
        self.max_player_id = max_player_id

    def send_and_resolve_all(
        self,
        messages: List[Message],
        poll_every: Optional[int] = 5,
        poll_for: Optional[int] = 60,
        *,
        stop_on_nomination: bool = False,
    ) -> int:
        """Sends all messages and monitors for responses until resolved.

        Args:
            message_handler: The MessageHandler instance to use.
            messages: List of Message objects to send.
            poll_every: Seconds between polling for responses.
            poll_for: Total seconds to poll before giving up."""
        
        print("\nSending emails to all players...", end="")
        # Send all messages
        for message in messages:
            # Add unique code to end of subject to help match replies
            message.subject += f" [ID: {id(message)}]"

            self.email_handler.send_email(
                to_address=message.address,
                subject=message.subject,
                body=message.body,
            )

        
        # print all messages that are passed into the function
        # all messages have components: priority, address, subject, body, resolved, response, playernumber, responseBody, expected_response_number

        print("Done")
        # for msg in messages: print(f"To {msg.address} subject '{msg.subject}' body '{msg.body}' resolved {msg.resolved} response {msg.response} playernumber {msg.playernumber} responsebody {msg.responseBody} expected responses {msg.expected_response_number}")


        # Monitor for responses until all messages are resolved or timeout
        unresolved_messages = [
            msg for msg in messages if not msg.resolved
        ]
        print(f"Waiting for {len(unresolved_messages)} message(s)", end="", flush=True)


        start_time = time.time()
        while time.time() - start_time < poll_for:
            time.sleep(poll_every)
            
            if not unresolved_messages:
                break  # All messages resolved
            # print number of messages still unresolved
            print(".", end="", flush=True)

            # Check for new emails
            new_emails = self.email_handler.check_unread()

            if new_emails:
                print(f"found {len(new_emails)} email(s)")

            for email in new_emails:
                # print(f"Processing email from {email.get('from')} with subject '{email.get('subject')}'")
                # go through and check if any global commands are present.
                # normalise the subject
                
                email_subj = normalize_subject(email.get("subject") or "")
                email_from = (email.get("from") or "").strip().casefold()

                for msg in unresolved_messages:
                    # print(f"Checking against message to {msg.address} with subject '{msg.subject}'")

                    # Normalize and compare sender addresses (tolerant of display names)
                    msg_addr = (msg.address or "").strip().casefold()

                    msg_subj = normalize_subject(msg.subject)

                    if addresses_match(email_from, msg_addr) and email_subj == msg_subj:
                        # Parse response integers from email body
                        clean_body = email.get("clean_body")
                        if msg.expected_response_number > 0:
                            response_ints = self.email_handler.extract_ints_from_body(clean_body)

                            msg.response = response_ints
                            msg.responseBody = clean_body

                            # Mark as resolved if expected number of responses received
                            if (
                                len(response_ints) == msg.expected_response_number
                                and all(0 < n <= self.max_player_id for n in response_ints)
                                and (len(response_ints) != 2 or response_ints[0] != response_ints[1])
                                and (msg.canChooseSelf or all(n != msg.playernumber for n in response_ints))
                            ):
                                msg.resolved = True
                                # record the time this valid response was accepted
                                try:
                                    msg._response_time = time.time()
                                except Exception:
                                    pass
                                print(f"accepted response from {msg.playerName}")

                            else:
                                print(f"rejecting response from {msg.playerName} sending again")
                                # send message again.
                                self.email_handler.send_email(msg.address, msg.subject, msg.body+"\n Your previous response was invalid. Please try again.")
                        else:
                            # No expected responses: accept optionally provided integers.
                            # However, if the message was sent to a dead player, do not
                            # treat any integers they send as nominations — mark resolved
                            # but clear responses.
                            if getattr(msg, "is_dead", False):
                                msg.response = []
                                msg.responseBody = clean_body
                                msg.resolved = True
                                print(f"ignored response from dead player {msg.playerName}")
                            else:
                                response_ints = []
                                try:
                                    response_ints = self.email_handler.extract_ints_from_body(clean_body) or []
                                except Exception:
                                    response_ints = []

                                # Keep only integers within the allowed id range
                                valid_ints = [n for n in response_ints if isinstance(n, int) and 0 < n <= self.max_player_id]

                                # If the handler was given an allowed_nomination_ids set, use
                                # it to filter valid ints to only alive players.
                                allowed_set = getattr(self, "allowed_nomination_ids", None)
                                if allowed_set is not None:
                                    allowed_ints = [n for n in valid_ints if n in allowed_set]
                                else:
                                    allowed_ints = valid_ints

                                if valid_ints and not allowed_ints:
                                    # The player provided integers, but none referred to
                                    # currently-allowed (alive) players. Reject and ask
                                    # them to try again.
                                    print(f"rejecting invalid nomination from {msg.playerName}; asking to retry")
                                    self.email_handler.send_email(msg.address, msg.subject, msg.body + "\n Your previous response was invalid. Please try again.")
                                    # do not mark resolved so we continue waiting
                                else:
                                    # Accept either no integers or a set of allowed ints
                                    msg.response = allowed_ints
                                    msg.responseBody = clean_body
                                    msg.resolved = True
                                    # record the time this optional response was accepted
                                    try:
                                        msg._response_time = time.time()
                                    except Exception:
                                        pass
                                    print(f"accepted response from {msg.playerName}")
                unresolved_messages = [
                    msg for msg in messages if not msg.resolved
                ]

                # If requested, return early as soon as any optional integer
                # nomination is received in any message's response list — but
                # ignore responses from dead players.
                if stop_on_nomination:
                    for m in messages:
                        if getattr(m, "response", None) and not getattr(m, "is_dead", False):
                            # check that at least one of the integers is a valid player id
                            if any(isinstance(n, int) and 0 < n <= self.max_player_id for n in m.response):
                                print("Nomination detected; returning early from message handler.")
                                return messages

                print(f"Waiting for {len(unresolved_messages)} message(s)", end="", flush=True)

                orig_from = (email.get("from") or "").strip()
                body_text = (email.get("clean_body") or email.get("body") or "").casefold()
                trigger = "who are we waiting for"

                # Trigger if the phrase appears in the subject or anywhere in the body
                if trigger in (email_subj or "") or trigger in (body_text or ""):
                    pending_players = [msg.playerName for msg in unresolved_messages]
                    if pending_players:
                        response_body = "Waiting for responses from: " + ", ".join(pending_players)
                    else:
                        response_body = "No pending responses."
                    self.email_handler.send_email(
                        to_address=orig_from,
                        subject="Re: We are waiting for...",
                        body=response_body,
                    )

        # Return the number of resolved messages
        return messages
    

def addresses_match(a: str, b: str) -> bool:
    return a == b or a in b or b in a

# Normalize subjects by removing common reply prefixes like "Re:" and compare case-insensitively
def normalize_subject(s: str) -> str:
    if s is None:
        return ""
    s2 = s.strip()
    # remove leading Re: or Fw: (possibly repeated), case-insensitive
    s2 = re.sub(r'^(?:\s*(?:re|fw|fwd)\s*:)+\s*', "", s2, flags=re.IGNORECASE)
    return s2.casefold()