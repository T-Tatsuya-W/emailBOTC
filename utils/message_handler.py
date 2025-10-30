"""Message handling utilities.

Provides a small Message data container and a MessageHandler which manages a
stack of unresolved messages. This is intentionally minimal: it stores
outstanding messages, supports adding new messages, resolving by id, and
retrieving unresolved messages (LIFO order).

Later this will be wired to `EmailHandler` to send messages and route
responses back to the originating player objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import uuid


@dataclass
class Message:
    """Represents an outgoing message waiting for a reply.

    Fields:
    - id: unique identifier for the message (str)
    - player_id: identifier of the originating player (str)
    - to_email: destination email address (str)
    - subject: subject used to correlate replies (str)
    - body: message body (str)
    - resolved: whether a response has been received (bool)
    - response: optional response payload once resolved (Optional[str])
    """

    player_id: str
    to_email: str
    subject: str
    body: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resolved: bool = False
    response: Optional[str] = None
    # how many integer values are required in a valid reply (0, 1, or 2)
    required_ints: int = 0
    # optional batch id so multiple messages can be grouped together; when all
    # messages in a batch are resolved a batch callback will be invoked
    batch_id: Optional[str] = None


class MessageHandler:
    """Manage a stack of unresolved Message objects.

    Behavior:
    - add(msg): push a message onto the stack of unresolved messages
    - pop_unresolved(): pop the most-recent unresolved message (LIFO)
    - resolve(message_id, response): mark the message resolved and attach a response
    - get_unresolved(): list unresolved messages in LIFO order
    - find_by_player(player_id): list unresolved messages for a player
    """

    def __init__(self) -> None:
        # internal list acts as a stack; append() pushes, pop() pops
        self._stack: List[Message] = []
        # batch callbacks: batch_id -> callable(list[Message])
        self._callbacks = {}
        # keep track of batches already fired to avoid double-calling
        self._fired_batches = set()

    def add(self, message: Message) -> None:
        """Add a Message to the unresolved stack."""
        if message.resolved:
            raise ValueError("Cannot add an already resolved message to handler")
        self._stack.append(message)

    def pop_unresolved(self) -> Optional[Message]:
        """Pop and return the most recently added unresolved Message.

        Returns None if no unresolved messages are present.
        """
        # pop until we find an unresolved (skip resolved entries)
        while self._stack:
            msg = self._stack.pop()
            if not msg.resolved:
                return msg
        return None

    def resolve(self, message_id: str, response: str, reopen_on_invalid: bool = False) -> bool:
        """Attempt to resolve the message with `message_id` using `response`.

        Validation: if the Message specifies `required_ints` (> 0) we will parse
        integer values from the response and only resolve if the count matches.

        If the response does not satisfy the requirement then:
        - if reopen_on_invalid is False -> do not close the message, return False
        - if reopen_on_invalid is True -> mark the original message resolved (storing
          the invalid response) and push a fresh Message with the same parameters
          onto the stack; return False.

        Returns True if the message was found and accepted (resolved), False otherwise.
        """
        import re

        for msg in self._stack:
            if msg.id == message_id and not msg.resolved:
                # check required ints
                req = int(msg.required_ints or 0)
                if req == 0:
                    # accept any response
                    msg.resolved = True
                    msg.response = response
                    if msg.batch_id:
                        self._maybe_fire_batch_callback(msg.batch_id)
                    return True

                found = re.findall(r"-?\d+", response or "")
                if len(found) == req:
                    msg.resolved = True
                    msg.response = response
                    # if this message belongs to a batch, maybe fire its callback
                    if msg.batch_id:
                        self._maybe_fire_batch_callback(msg.batch_id)
                    return True
                # invalid response -> automatically send a follow-up message that
                # politely asks the player to resend in the correct format.
                # Mark the original message resolved (storing the invalid response)
                # and push a fresh follow-up Message so the CLI or email adapter
                # can surface it to the player.
                msg.resolved = True
                msg.response = response

                # Construct a helpful follow-up body telling the sender what is
                # expected. Keep the subject similar so replies will still be
                # correlated.
                hint = ""
                if req == 1:
                    hint = "Please reply with exactly 1 integer (e.g. `3`)."
                elif req == 2:
                    hint = "Please reply with exactly 2 integers separated by spaces (e.g. `1 2`)."
                else:
                    hint = "Please reply with the expected response format."

                follow_body = f"Your previous response couldn't be understood. {hint}\n\nOriginal message:\n{msg.body}" 

                new_msg = Message(
                    player_id=msg.player_id,
                    to_email=msg.to_email,
                    subject=f"{msg.subject} - please resend in correct format",
                    body=follow_body,
                    required_ints=msg.required_ints,
                    batch_id=msg.batch_id,
                )
                self.add(new_msg)
                # indicate invalid (original message was not accepted)
                return False
        return False

    def get_unresolved(self) -> List[Message]:
        """Return a list of unresolved messages in LIFO order (newest first)."""
        unresolved = [m for m in self._stack if not m.resolved]
        # return newest first
        return list(reversed(unresolved))

    def find_by_player(self, player_id: str) -> List[Message]:
        """Return unresolved messages for a given player (newest first)."""
        return [m for m in self.get_unresolved() if m.player_id == player_id]

    def __len__(self) -> int:
        """Return count of unresolved messages."""
        return len([m for m in self._stack if not m.resolved])

    def register_callback(self, batch_id: str, callback) -> None:
        """Register a callback to be invoked when all messages for batch_id are resolved.

        The callback will be called with a single argument: list[Message].
        """
        self._callbacks[batch_id] = callback

    def _maybe_fire_batch_callback(self, batch_id: str) -> None:
        """If all messages in batch_id are resolved, call the registered callback once."""
        if batch_id in self._fired_batches:
            return

        msgs = [m for m in self._stack if m.batch_id == batch_id]
        if not msgs:
            return

        if all(m.resolved for m in msgs):
            cb = self._callbacks.get(batch_id)
            if cb:
                try:
                    cb(list(msgs))
                except Exception:
                    # swallow exceptions coming from callbacks to avoid breaking handler
                    pass
            self._fired_batches.add(batch_id)
