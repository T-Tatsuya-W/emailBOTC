# emailBOTC — email-driven game prototype

**Quickstart (Windows PowerShell)**

- Create and activate a virtualenv, then install requirements:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

- Run the demo:

```powershell
python main.py
```

- Run tests:

```powershell
python -m pytest -q
```

This repository is an early prototype of an email-driven game (a simplified
``BotC`` style night-phase demo). It contains a small email utility, a message
handler that sends prompts and polls for replies, a minimal game driver, and
unit tests that mock email operations so you can exercise the logic without
real SMTP/IMAP credentials.

## Current game flow (what the code does today)

1. `main.py` builds a small in-memory `players` list and calls `nightphase(players)`.
2. `nightphase` creates a `Message` dataclass instance per player describing the prompt
	(subject/body, expected number of integer responses, player id, etc.).
3. A `MessageHandler` (in `utils/message_handler.py`) is constructed with an
	`EmailHandler` instance and the messages. `MessageHandler.send_and_resolve_all`
	will:
	- send each player's prompt via `EmailHandler.send_email`,
	- poll for new messages using `EmailHandler.check_unread`,
	- match replies to outstanding messages (subject normalization + sender address),
	- extract integers from replies and validate them against the message's
	  `expected_response_number` and the configured `max_player_id`,
	- mark messages resolved when valid responses are received; otherwise it
	  re-sends the prompt with an error note.
4. When `send_and_resolve_all` completes, `nightphase` applies a simple priority
	loop to process resolved player actions (demo logic for roles such as Imp,
	Poisoner, Monk, Fortune Teller is included as a placeholder).

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
	- A small interactive demo harness for manual testing of `EmailHandler`.

- `tests/test_message_handler.py`
	- Unit tests which use a mocked `EmailHandler` to exercise `MessageHandler`'s
		logic without network I/O. The repository includes a pytest-style layout
		that shows how to provide a mock handler and sample inbox events.

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

The tests are written to avoid real SMTP/IMAP activity by injecting a mock
`EmailHandler` implementation. See `tests/test_message_handler.py` for the
fixture examples and test layout.

## Notes & known issues / assumptions


Known issues / assumptions:

- `main.py` is a prototype demo that uses a static `players` list and simple
	role-processing logic. It's a place to iterate on game behavior rather than a
	finished engine.
- Matching replies depends on normalized subject texts and sender addresses.
	Some email clients may rewrite subjects or headers which can break matching.
- The plain-text body cleaning (`EmailHandler._clean_body`) is a best-effort
	approach and may not remove every quoted block for complex HTML emails.

If you want, I can also:

- update or extend the unit tests to cover more game flows (examples: invalid
	response handling, duplicate responses, self-target validation), or
- add a small mocked runner that simulates replies so the night-phase can be
	exercised end-to-end in CI without real email credentials.

## Suggested next steps (small, low-risk)

- Update/align unit tests to the current `MessageHandler` API (rename or adapt tests to call `send_and_resolve_all`, or add the small adapter helpers the tests expect).
- Add a small example script that runs `main.py` end-to-end with a mocked `EmailHandler` so CI can exercise the game flow without real SMTP/IMAP.
- Add HTML->text fallback for `EmailHandler.check_unread` using `beautifulsoup4` if HTML-only messages need support.

If you'd like, I can now:

- update the unit tests to match the current `MessageHandler` API, and run the test suite, or
- add a mocked demo runner that simulates replies so you can run the night-phase locally without email credentials.

Tell me which of these you'd prefer and I'll implement it next.
