"""Simple Action dataclass for game controller to execute."""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Action:
    actor_id: str
    kind: str
    payload: Dict[str, Any]
