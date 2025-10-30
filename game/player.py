"""Player model for BOTC.

This is a simple, minimal Player implementation used as the project's new
starting point. It stores a few basic attributes needed by the game logic:

- `alive`: bool - whether the player is alive
- `can_vote`: bool - whether the player may cast votes
- `playername`: str - display name
- `player_email`: str - contact email
- `character`: optional string describing assigned character/role

Only the `kill()` method is implemented for now (sets `alive` to False).
"""
from __future__ import annotations
from typing import Optional
import uuid

# Import Message here to allow a Player to create Message objects and add
# them into a MessageHandler stack. Importing from utils is safe; if you
# later move MessageHandler to reference Player objects you might need to
# use a registry to avoid circular imports.
from utils.message_handler import Message
from .actions import Action


class Player:
    """Simple player container.

    Constructor arguments:
    - playername: str
    - player_email: str
    - character: Optional[str] (default: None)
    - can_vote: bool (default: True)
    - can_nominate: bool (default: True)
    - evil: bool (default: False)
    - drunk: bool (default: False)
    - poisoned: bool (default: False)
    """

    def __init__(
        self,
        playername: str,
        player_email: str,
        player_id: Optional[str] = None,
        character: Optional[str] = None,
        can_vote: bool = True,
        evil: bool = False,
        drunk: bool = False,
        poisoned: bool = False,
    ) -> None:
        self.playername = str(playername)
        self.player_email = str(player_email)
        # allow a custom player_id (useful for tests/fixtures); otherwise generate a UUID
        self.player_id = player_id or str(uuid.uuid4())
        self.character = character
        # how many integer values we expect in a response to messages from this player
        # (0, 1, or 2)
        self.expected_ints = 0
        # booleans
        self.alive = True
        self.can_vote = bool(can_vote)
        self.can_nominate = True
        # alignment flag
        self.evil = bool(evil)
        # status effects
        self.drunk = bool(drunk)
        self.poisoned = bool(poisoned)

    def send_message(self, handler, to_email: str, subject: str, body: str, *, batch_id: str | None = None, required_ints: int | None = None) -> Message:
        """Create a Message for this player and add it to the given MessageHandler.

        Args:
            handler: MessageHandler instance (from utils.message_handler)
            to_email: destination email address
            subject: subject used to correlate replies
            body: message body

        Returns:
            The Message instance that was created and added to the handler.
        """
        # include how many integers we expect in a reply
        msg = Message(
            player_id=self.player_id,
            to_email=to_email,
            subject=subject,
            body=body,
            required_ints=(self.expected_ints if required_ints is None else required_ints),
            batch_id=batch_id,
        )
        handler.add(msg)
        return msg

    def create_action(self, message: Message) -> Action:
        """Convert a resolved Message into an Action.

        Default behaviour: extract integers from the message response and return
        an Action of kind 'numbers' with the parsed integers. Subclasses (player
        types) can override this to implement role-specific parsing and action
        creation.
        """
        import re

        nums = [int(n) for n in re.findall(r"-?\d+", message.response or "")]
        return Action(actor_id=self.player_id, kind="numbers", payload={"numbers": nums, "message_id": message.id})

    def kill(self) -> None:
        """Mark the player as dead.

        This simply flips `alive` to False for now. More complex death
        handling (events, logging, tombstones) can be added later.
        """
        self.alive = False
        # when a player is killed they can no longer nominate
        self.can_nominate = False

    def is_alive(self) -> bool:
        return bool(self.alive)

    def __repr__(self) -> str:
        return (
            f"Player(player_id={self.player_id!r}, playername={self.playername!r}, email={self.player_email!r}, "
            f"character={self.character!r}, alive={self.alive}, can_vote={self.can_vote}, "
            f"can_nominate={self.can_nominate}, evil={self.evil}, "
            f"drunk={self.drunk}, poisoned={self.poisoned})"
        )
