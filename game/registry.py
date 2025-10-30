"""Player registry to map player_id -> Player instances.

Lightweight utility used by GameController and Message routing to find the
Player object associated with a player_id.
"""
from typing import Dict, Optional


class PlayerRegistry:
    def __init__(self) -> None:
        self._players: Dict[str, object] = {}

    def register(self, player) -> None:
        self._players[player.player_id] = player

    def unregister(self, player_id: str) -> None:
        self._players.pop(player_id, None)

    def get(self, player_id: str) -> Optional[object]:
        return self._players.get(player_id)

    def all_players(self):
        return list(self._players.values())

    def clear(self) -> None:
        self._players.clear()
