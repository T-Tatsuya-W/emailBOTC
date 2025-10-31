# emailBOTC

A small utility for sending and reading emails using SMTP and IMAP, focused on programmatic workflows and reliable in-thread replies.

This repository contains a lightweight `EmailHandler` in `utils/email_handler.py` that:

- sends emails via SMTP (with optional in-thread replies), and
- checks for unread messages via IMAP and returns full plain-text bodies with cleaned replies.

The implementation intentionally prefers IMAP UIDs for stable message references and provides helpers for extracting and cleaning message bodies (removes common reply headers and quoted blocks).

## Contents

- `utils/email_handler.py` — main EmailHandler class (send & check_unread).
- `main.py` — small interactive harness for manual testing (send / list unread).
- `requirements.txt` — Python dependencies used by the project.

## Design contract (short)

- Inputs: environment config via `.env` (or explicit constructor args), and method inputs such as `to_address`, `subject`, `body`, and `reply_uid`.
- Outputs: boolean success for sends, and a list of message dictionaries for `check_unread` with both sequence `id` and stable numeric `uid`, plus `body` and `clean_body`.
- Error modes: ValueError for missing config; RuntimeError for network/IMAP/SMTP failures; methods attempt best-effort cleanup and reporting.

## Required configuration

The handler reads configuration from environment variables (via `python-dotenv`) or you can pass them directly to the `EmailHandler` constructor. Add a `.env` file at the repo root with these keys:

```
EMAIL_ADDRESS=you@example.com
EMAIL_APP_PASSWORD=<app-password-or-smtp-password>
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
IMAP_SERVER=imap.example.com
IMAP_PORT=993
```

Make sure `requirements.txt` contains `python-dotenv` (it does in this repo). Then install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Usage examples

Example: basic send

```python
from utils.email_handler import EmailHandler

eh = EmailHandler()  # reads from .env by default
success = eh.send_email(
	to_address='friend@example.com',
	subject='Hello from emailBOTC',
	body='This is a test message sent from emailBOTC.'
)
print('sent?', success)
```

Replying to a message by UID (stable identifier)

If you have an IMAP UID for a message (for example from `check_unread`), pass it to `send_email` as `reply_uid` and the handler will fetch the original message, extract the original Message-ID and reply headers, and set proper `In-Reply-To` / `References` headers automatically.

```python
from utils.email_handler import EmailHandler

eh = EmailHandler()
reply_uid = 12345  # an IMAP UID you previously saved
ok = eh.send_email(
	to_address=None,               # will default to original Reply-To or From if None
	subject='Re: original subject',
	body='Thanks — here is my reply',
	reply_uid=reply_uid
)
```

Notes:
- `to_address=None` when `reply_uid` is set means the handler will determine the correct recipient (Reply-To or From) from the original message.
- `thread_id` is a fallback synthetic header (if you don't have a real Message-ID) that helps group messages but is not recommended over `reply_uid`.

Checking unread messages

```python
from utils.email_handler import EmailHandler

eh = EmailHandler()
msgs = eh.check_unread(mark_seen=False)
for m in msgs:
	print('seq_id:', m['id'], 'uid:', m['uid'])
	print('from:', m['from'])
	print('subject:', m['subject'])
	print('clean_body:')
	print(m['clean_body'])
	print('---')
```

Each message dict includes these keys (example):

```json
{
  "id": "12",
  "uid": 34567,
  "from": "Alice <alice@example.com>",
  "subject": "Meeting notes",
  "date": "Fri, 31 Oct 2025 10:15:00 +0000",
  "body": "Full extracted plain-text body including quoted text and original message",
  "clean_body": "Only the new content, with reply headers and quoted blocks removed"
}
```

`id` is the IMAP sequence number (string). `uid` is the IMAP UID (integer) and is stable across the mailbox; prefer `uid` for referencing messages in code.

## What `clean_body` tries to do

- Truncate at common reply separators like lines matching `^On .*wrote:$` and `-----Original Message-----`.
- Remove lines that start with `>` (quoted lines).
- Provide a compact block that contains the new reply text and not the original message.

This is best-effort. For complex multi-part HTML or unusual clients, some quoted content may remain; see troubleshooting below.

## Example flows / use cases

- Automated replies to support tickets: poll `check_unread`, parse `clean_body` to understand the request, and `send_email(reply_uid=uid, body=...)` to reply in-thread.
- Notifications and threaded follow-ups: send an initial message, store the returned `uid` from `check_unread` when people reply, and use `reply_uid` to address future replies properly.
- Human-in-the-loop workflows: `main.py` provides an interactive way to send and list unread messages during development.

## Troubleshooting

- Missing config: if `.env` is absent or variables missing, the constructor will raise `ValueError`. Confirm `.env` or pass params explicitly.
- IMAP/SMTP auth errors: ensure `EMAIL_APP_PASSWORD` is correct and that the account allows SMTP/IMAP access (app password, less-secure apps, or OAuth as appropriate).
- HTML-only messages: currently the handler extracts plain-text parts and falls back to decoding simple payloads; HTML-only messages may not be converted perfectly. Consider adding an HTML->text fallback (future work).
- IMAP IDLE / long-lived sockets: earlier work included IDLE polling, but it produced socket timeout issues in some environments — IDLE was removed in favor of simple checks. If you need IDLE, consider using a robust library or dedicated long-running worker and thorough error handling.

## Next steps (suggested improvements)

- Add a `reply_to_uid(uid, body, subject=None, reply_all=False)` convenience method.
- Add HTML-to-text fallback for HTML-only messages (e.g., using `beautifulsoup4` or `html2text`).
- Add unit tests (mock SMTP/IMAP) and a CI workflow.

## Where to look in the code

- `utils/email_handler.py` — the EmailHandler and helpers (send_email, check_unread, _clean_body).
- `main.py` — simple manual CLI to exercise the handler.

If you'd like, I can also add a short example script that polls for unread messages and automatically replies using `reply_uid` — say the word and I'll implement it next.
