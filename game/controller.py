"""GameController skeleton to orchestrate rounds, prompt players and execute actions."""
from __future__ import annotations

from typing import List, Dict, Optional
import uuid

from .registry import PlayerRegistry
from .actions import Action
from utils.message_handler import MessageHandler, Message


class GameController:
    """Orchestrates players, prompting and executing actions.

    This is a minimal skeleton intended to be extended. It demonstrates the
    round flow: create players, send a batch of messages (tagged by batch_id),
    register a callback to be invoked when the batch completes, convert
    messages to Actions and execute them.
    """

    def __init__(self, players_configs: List[Dict], message_handler: MessageHandler):
        self.registry = PlayerRegistry()
        self.message_handler = message_handler
        self.players: List = []
        # simple state to hold last actions executed (useful for tests)
        self.last_actions: List[Action] = []

        for cfg in players_configs:
            # construct Player lazily to avoid importing cycle in tests
            from game.player import Player

            p = Player(cfg.get("playername"), cfg.get("player_email"), player_id=cfg.get("player_id"))
            # allow config to set expected_ints
            if "expected_ints" in cfg:
                p.expected_ints = int(cfg["expected_ints"]) or 0
            self.registry.register(p)
            self.players.append(p)

    def start_round(self, prompt_text: str = "Action", required_ints: Optional[int] = None) -> str:
        """Send prompts to all players, returning the batch_id.

        The required_ints argument overrides each player's expected_ints for this
        round; if None the player's own expected_ints is used.
        """
        batch_id = str(uuid.uuid4())

        # register a callback for when the batch completes
        self.message_handler.register_callback(batch_id, lambda msgs: self._on_batch_resolved(batch_id, msgs))

        # send each player a message
        for p in self.players:
            ri = required_ints if required_ints is not None else getattr(p, "expected_ints", 0)
            subject = f"{prompt_text} [{batch_id}]"
            body = prompt_text
            p.send_message(self.message_handler, p.player_email, subject, body, batch_id=batch_id, required_ints=ri)

        return batch_id

    def _on_batch_resolved(self, batch_id: str, messages: List[Message]) -> None:
        """Convert messages to actions and execute them."""
        actions = self._convert_messages_to_actions(messages)
        self.execute_actions(actions)

    def _convert_messages_to_actions(self, messages: List[Message]) -> List[Action]:
        """Convert messages into actions by delegating to each Player.

        This allows player classes to implement their own conversion logic
        (for example different roles producing different Action kinds).
        """
        actions: List[Action] = []
        for m in messages:
            player = self.registry.get(m.player_id)
            if player is None:
                # fallback: simple numbers action
                import re

                nums = [int(n) for n in re.findall(r"-?\d+", m.response or "")]
                actions.append(Action(actor_id=m.player_id, kind="numbers", payload={"numbers": nums, "message_id": m.id}))
            else:
                # allow player.create_action to return either an Action or list[Action]
                result = player.create_action(m)
                if isinstance(result, list):
                    actions.extend(result)
                else:
                    actions.append(result)

        return actions

    def execute_actions(self, actions: List[Action]) -> None:
        """Execute actions - minimal behavior: store last_actions and attach
        a 'last_numbers' attribute on the player for testing and inspection.
        """
        self.last_actions = actions
        for a in actions:
            p = self.registry.get(a.actor_id)
            if p:
                setattr(p, "last_numbers", a.payload.get("numbers"))
