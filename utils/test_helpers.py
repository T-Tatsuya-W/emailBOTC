from typing import Any, Dict, List, Optional, Union

from utils.message_handler import Message
from utils.email_handler import EmailHandler


class SimpleMessageHandler:
    """A tiny MessageHandler replacement for tests.

    It accepts a `responses` mapping keyed by player number (int) or email
    (str). Values can be:
      - a list of ints (already-parsed responses),
      - an int (single response), or
      - a string (will be parsed for integers using EmailHandler).

    The handler implements a minimal `send_and_resolve_all` method which
    populates the provided Message objects' `response`, `responseBody` and
    `resolved` fields according to the same validation rules used by the
    production `MessageHandler`.
    """

    def __init__(self, responses: Optional[Dict[Union[int, str], Any]] = None):
        self.responses = responses or {}
        self.messages: List[Message] = []
        self.max_player_id: int = 0

    def send_and_resolve_all(self, messages: List[Message], poll_every=None, poll_for=None) -> List[Message]:
        # record messages and use max_player_id set by caller (nightphase)
        self.messages = messages

        for msg in messages:
            # find response by playernumber first, then by address
            resp = self.responses.get(msg.playernumber)
            if resp is None:
                resp = self.responses.get(msg.address)

            if resp is None:
                # if no response is configured, resolve only messages that
                # expect zero responses
                if msg.expected_response_number == 0:
                    msg.resolved = True
                continue

            # normalize response into list[int]
            if isinstance(resp, list):
                ints = resp
            elif isinstance(resp, int):
                ints = [resp]
            else:
                # accept strings like "2" or "2 3"
                ints = EmailHandler().extract_ints_from_body(str(resp))

            msg.response = ints
            msg.responseBody = str(resp)

            # validate using the same rules as MessageHandler
            if (
                len(ints) == msg.expected_response_number
                and all(0 < n <= self.max_player_id for n in ints)
                and (len(ints) != 2 or ints[0] != ints[1])
                and (msg.canChooseSelf or all(n != msg.playernumber for n in ints))
            ):
                msg.resolved = True

        return messages
