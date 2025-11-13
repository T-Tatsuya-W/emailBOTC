# Tests summary (emailBOTC)

This file documents the test strategy and the current tests in this repository, plus short suggestions for next tests to add.

## How tests are organized
- Unit / logic tests (fast, isolated):
  - `tests/test_perform_night_actions.py` — constructs `Message` objects directly and calls `perform_night_actions(players, actions)` to exercise role-resolution logic (Imp, Poisoner, Monk, Fortune Teller). These are the fastest, lowest-level checks.
  - `tests/test_perform_nightphase_roles.py` — (kept as skipped) historically contained similar unit tests; the canonical unit tests live in `test_perform_night_actions.py`.

- Integration tests (exercise the message handling + nightphase):
  - `tests/test_nightphase.py` — injects an `AutoReplyEmailHandler` mock to simulate incoming email replies. This verifies subject matching, reply parsing and end-to-end `nightphase(...)` behavior.
  - `tests/test_nightphase_simple.py` — uses `utils/test_helpers.SimpleMessageHandler` to bypass IMAP/email semantics and provide deterministic per-player responses to `nightphase(...)`. This is a lightweight integration test that exercises `nightphase` but avoids email plumbing.

- Email/message handler tests:
  - `tests/test_message_handler.py` — tests around the `MessageHandler` and email matching/validation behaviour.

## What each file focuses on
- `test_perform_night_actions.py`: role resolution logic, priorities, and interactions (e.g., Monk protection, Poisoner marking poison flag, poisoned Monk failing to protect). Use these for quick TDD feedback.
- `test_nightphase_simple.py`: run full `nightphase` with a simple, deterministic message handler (fast integration).
- `test_nightphase.py`: end-to-end integration including the (mock) email layer, subject normalization, inbox consumption. Keep a small set of these to exercise the I/O surface.
- `test_message_handler.py`: messaging edge cases and message parsing/validation.

## Why we keep both 'simple' and 'full' integration tests
- Fast deterministic tests (`test_nightphase_simple.py`) are great for development and CI where speed and determinism matter.
- Full integration tests (`test_nightphase.py`) validate the message/email plumbing which the simple handler does not exercise. They catch regressions in parsing/matching logic.

## How to run tests locally
Install dependencies (once):

```powershell
python -m pip install -r .\requirements.txt
```

Run all tests:

```powershell
python -m pytest -q
```

Run a single file (fast feedback):

```powershell
python -m pytest tests/test_perform_night_actions.py -q
```

Run a single test function:

```powershell
python -m pytest tests/test_perform_night_actions.py::test_poisoned_monk_fails_and_imp_kills_target -q
```

## Tests added in this work (high level)
- Unit tests for `perform_night_actions` covering:
  - Imp kills unprotected targets
  - Monk protection prevents Imp when unpoisoned
  - Poisoner marks poisoned flag (does not kill immediately)
  - Poisoned Monk cannot protect
  - Poisoned Monk fails to protect, allowing Imp kill later in the same night

- Integration tests covering `nightphase` with both a simple deterministic
  handler and a mock email handler to cover parsing/subject-matching.

## Suggested next tests (priority order)
1. Edge-case validation tests (high priority)
   - Self-targeting rules (canChooseSelf True/False). Ensure invalid self-targets are rejected.
   - Invalid IDs (out-of-range numbers) are rejected and re-prompted.
   - Two-choice validation: duplicate choices (e.g., "2 2") should be rejected.

2. Multi-night flows (medium priority)
   - Poison carryover: a poisoned player dies at the start of the next night (or per desired rules).
   - Interaction sequences across nights (e.g., poisoner poisons, next night Imp or other roles act).

3. Role coverage (medium-low priority)
   - Add tests for additional roles you implement (Washerwoman, Soldier, Fortune Teller behavior beyond no-op).
   - Test role promotions (Imp dying and another Evil becoming Imp) if that mechanic is used.

4. Test tooling and quality (low priority)
   - Convert `SimpleMessageHandler` and `AutoReplyEmailHandler` into pytest fixtures for reuse.
   - Consolidate integration tests into `tests/test_nightphase_integration.py` for clarity.
   - Add quick property-based tests (hypothesis) for message parsing if needed.

## Notes
- I preserved some historical test files but marked duplicates as skipped to reduce clutter while keeping history.
- If you prefer, I can delete skipped files instead of skipping them.

---
If you want, I can add the first edge-case tests (self-targeting and invalid ids) next — say the word and I'll implement them and run the suite.
