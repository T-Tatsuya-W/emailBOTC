# emailBOTC — email-driven game toolkit

This repository contains an early-stage email-driven game prototype where game prompts are sent to players via email and player actions are read back from email replies. The codebase provides:

- an `EmailHandler` that sends and reads plain-text emails (SMTP + IMAP),
- a small `Message` model and `MessageHandler` that sends game prompts and polls for replies, and
- a minimal game driver (`main.py`) with a placeholder night-phase implementation demonstrating how messages are created and processed.

This README documents the current game flow, the location of key classes/functions, how to configure and run the project, and a few notes/assumptions.

## Current game flow (what the code does today)

1. The driver in `main.py` constructs an in-memory `players` list and calls `nightphase(players)`.
2. `nightphase` creates a `Message` object for each player describing their night prompt (how many integer responses are expected and other metadata).
3. The `MessageHandler` (in `utils/message_handler.py`) is created with an `EmailHandler` instance and the messages and calls `send_and_resolve_all` to:
	 - send each player's prompt email (via `EmailHandler.send_email`),
	 - poll the mail account using `EmailHandler.check_unread` for replies,
	 - match incoming replies to outstanding messages by normalized subject and sender address,
	 - extract integers from the reply body and validate them against `expected_response_number` and `max_player_id`,
	 - mark messages resolved when valid responses are received (otherwise re-send the prompt with an error message).
4. After `send_and_resolve_all` returns, `nightphase` processes resolved player actions according to role priorities (a simplified priority loop is implemented for roles like "Imp", "Poisoner", "Monk", etc.).

Notes about this flow:
- Matching replies depends on normalized subject text and sender addresses. Subjects are augmented with a unique id on send to reduce collisions.
- Responses are parsed as integers (player id numbers). The handler enforces simple validation rules (range, no duplicate pair responses, and self-choice rules).
- The implementation is intentionally simple and synchronous (polling). A production implementation could use IMAP IDLE, background workers, or a message queue.

## File / class / function organization

- `main.py`
	- parse_cli(argv=None) -> Optional[int]: parse optional integer CLI arg.
	- main() -> None: builds demo `players` list and invokes the `nightphase`.
	- nightphase(players: list) -> list: constructs `Message` objects for each player, uses `MessageHandler` to send and resolve prompts, then runs simple role-priority action handling.
	- get_player_by_number(players, number) -> Optional[dict]: helper to find a player dict by id.

- `utils/email_handler.py`
	- class EmailHandler
		- __init__(...): reads config from env or constructor args.
		- _ensure_config(): validate required config is present.
		- _clean_body(body: str) -> str: best-effort removal of quoted/previous message content.
		- extract_ints_from_body(body: str) -> List[int]: find integer tokens in the message body.
		- send_email(to_address, subject, body, thread_id=None, reply_uid=None) -> bool: send plain-text email; if `reply_uid` is provided the original message is fetched and threading headers set.
		- check_unread(mark_seen: bool = False) -> List[Dict[str, Any]]: fetch unread messages from INBOX, extract plain-text body and `clean_body`, return sequence id and UID.

	EmailHandler expects these environment variables (or constructor overrides): `EMAIL_ADDRESS`, `EMAIL_APP_PASSWORD`, `SMTP_SERVER`, `SMTP_PORT` (default 587), `IMAP_SERVER`, `IMAP_PORT` (default 993).

- `utils/message_handler.py`
	- @dataclass Message: fields include priority, resolved, response (List[int]), address, subject, body, playernumber, responseBody, expected_response_number, playerName, canChooseSelf.
	- class MessageHandler
		- __init__(email_handler=None, messages=None, max_player_id=0)
		- send_and_resolve_all(messages, poll_every=5, poll_for=60) -> List[Message]: sends prompts and polls using the provided `email_handler` until messages are resolved or timeout.
		- addresses_match(a, b) and normalize_subject(s) — small helpers used by the handler.

- `utils/demo_email_handler.py`
	- A small interactive demo harness that can send a test message, list unread messages, or start a periodic sender. Useful for manual testing outside the game flow.

- `tests/test_message_handler.py`
	- A set of unit tests that currently exercise MessageHandler behaviors. Note: some tests reference helper names that used to exist; the code and test expectations may be slightly out-of-sync. See "Notes & known issues" below.

## Configuration and running

1. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

2. Create a `.env` file at the project root (or set env vars) with at minimum:

```
EMAIL_ADDRESS=you@example.com
EMAIL_APP_PASSWORD=<app-password>
SMTP_SERVER=smtp.example.com
IMAP_SERVER=imap.example.com
```

3. Run the minimal game demo (sends prompts and polls using values in `main.py`):

```powershell
python main.py
```

4. Use the demo harness interactively:

```powershell
python utils/demo_email_handler.py
```

5. Running tests:

```powershell
python -m pytest -q
```

Note: the repository uses simple unit tests that mock the `EmailHandler`. Because the test file and the current `MessageHandler` implementation have diverged slightly (some helper names and APIs changed during development), tests may need small updates to match the current `MessageHandler` API.

## Notes & known issues / assumptions

- The game code in `main.py` is a prototype and uses a static `players` list and simple role-handling logic. It is not a finished game engine; it's an integration demo showing how email prompts and replies could be wired into a turn-based/night-phase flow.
- Reply matching relies on normalized subject and sender address; if email clients rewrite subjects aggressively this may fail.
- `EmailHandler._clean_body` is best-effort and may not strip all quoted content for complex HTML messages.
- Tests in `tests/test_message_handler.py` may reference older API names (for example `parse_response_integers`, `monitor_until_resolved`, or `send_night_emails`) — these need to be reconciled with `MessageHandler.send_and_resolve_all` and the current helpers.

## Suggested next steps (small, low-risk)

- Update/align unit tests to the current `MessageHandler` API (rename or adapt tests to call `send_and_resolve_all`, or add the small adapter helpers the tests expect).
- Add a small example script that runs `main.py` end-to-end with a mocked `EmailHandler` so CI can exercise the game flow without real SMTP/IMAP.
- Add HTML->text fallback for `EmailHandler.check_unread` using `beautifulsoup4` if HTML-only messages need support.

If you'd like, I can now:

- update the unit tests to match the current `MessageHandler` API, and run the test suite, or
- add a mocked demo runner that simulates replies so you can run the night-phase locally without email credentials.

Tell me which of these you'd prefer and I'll implement it next.
