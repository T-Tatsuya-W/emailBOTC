# emailBOTC — Email-based Battle of the Caste (BOTC)

Small, test-driven Python implementation of an email-mediated social-deduction game (a lightweight "Werewolf"/Mafia variant) used for prototyping and demonstration. The project sends prompts and collects responses over email (or a demo handler) and resolves day/night phases by role.

**Contents**
- **Run**: how to run the system locally and run tests.
- **Files**: map of main files and purpose.
- **Player stats / fields**: the player model fields used by the engine.
- **Implemented features**: what roles and flows are implemented today.
- **Extending**: notes on adding roles or adapting email behaviour.

**Requirements**
- Python 3.9+ recommended
- Project dependencies are in `requirements.txt` (currently `pytest` and `python-dotenv`).

**Quick Start**

1. Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. To run the interactive/demo script (if available) or the main runner:

```powershell
python main.py
```

main.py uses the `utils/demo_email_handler.py` or `utils/email_handler.py` depending on your environment and configuration. If you want to use real email sending/receiving, configure the environment variables (see `utils/email_handler.py` and `.env` usage) and provide IMAP/SMTP account details.

3. Run the test suite locally:

Use the Python module invocation so the correct interpreter/venv is used on both Windows and Linux.

PowerShell (Windows):

```powershell
# activate your venv first if using one
# .\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Bash (Linux/macOS):

```bash
# activate your venv first if using one
# source .venv/bin/activate
python -m pytest -q
```

To run only the tests directory:

```bash
python -m pytest tests -q
```

**File overview**
- `main.py` — small runner that wires together `player_factory`, `dayphase` and `nightphase`.
- `requirements.txt` — python dependencies for testing and dotenv.
- `pytest.ini` — pytest settings.

- `utils/`
  - `email_handler.py` — IMAP/SMTP email I/O, robust handling for transient IMAP/SSL issues.
  - `demo_email_handler.py` — a local/demo message handler that simulates sending/receiving for development.
  - `message_handler.py` — core message/response orchestration, subject token generation and normalization, and polling logic.
  - `dayphase.py` — day-phase logic: nominations, iterative nomination→voting rounds, vote collection and lynch resolution.
  - `nightphase.py` — night-phase logic: build prompts by role, collect night actions, and resolve them deterministically by priority.
  - `player_factory.py` — canonical roster and runtime player setup (role assignment rules, canonical slots, and special flags like `first_night_only`).
  - `settings.py` — centralized polling defaults (e.g. `DEFAULT_POLL_EVERY`, `DEFAULT_POLL_FOR`).

- `tests/` — pytest-based unit tests covering game flows and characters.

**Player model: fields and meaning**
Every player is represented as a Python `dict` with a set of well-known keys used across the engine. Key fields you will see and can rely on:

- **`id`**: numeric player id (unique integer)
- **`name`**: display name
- **`email`**: email address (used by message handlers)
- **`role`**: role name (e.g., `Imp`, `Fortune Teller`, `Monk`, `Soldier`, `Poisoner`, `Investigator`, `Villager`)
- **`dead`**: boolean; True when the player has been killed or lynched
- **`poisoned`**: boolean; True when the player was poisoned during the night (affects some role outputs)
- **`protected`**: boolean; True if protected (e.g., by Monk)
- **`drunk`**: boolean; True if role outputs are inverted/noisy for this player
- **`nightActionPriority`**: integer (1-4) used to resolve night actions in priority order
- **`nightResponse`**: integer number of expected response integers in night prompt (0 for no target expected)
- **`first_night_only`**: boolean; role acts only on first night if True
- **`skip_first_night`**: boolean; role does not act on first night if True
- **`canVote`**: boolean; whether a dead player is allowed a ghost vote

Additional per-player metadata attached during resolution:
- **`info_for_player`**: either a boolean (Fortune Teller result) or a string (Investigator readable message) — used by day messages.
- **`info_targets`**: list of player ids that were the targets of an inquiry (e.g., Fortune Teller or Investigator suspects)
- **`info_action`**: short action name such as `'investigate'` used to format readable lines in day emails
- **`last_night_announcement`**: public summary text describing who died during last night (prepended to day messages)
- **`last_day_announcement`**: public summary text describing the day's lynch outcome (prepended to night messages)

These fields are intentionally flat and simple so message composition code in `dayphase.py` and `nightphase.py` can format emails without tight coupling to role classes.

**Implemented features (current state)**
- Email handling:
  - Robust IMAP/SMTP handling with defensive recovery for SSL/EOF issues.
  - A subject token scheme that appends a stable token (timestamp-ms + short uuid) to outgoing message subjects and matches replies reliably.

- Game flow:
  - Day phase supports iterative nomination→voting rounds within a day window. The handler stops early when a nomination arrives, then proceeds to voting for that nominee.
  - Ghost votes: dead players may have a single ghost vote controlled by `canVote`.
  - Majority logic: nominations only succeed when they reach a computed majority threshold.

- Night phase and roles:
  - Priority-based night resolution with concise one-line terminal logs for each action.
  - Implemented roles: `Imp` (killer), `Fortune Teller` (investigates two players), `Monk` (protects), `Soldier`, `Poisoner`, and `Investigator` (first-night role).
  - `Fortune Teller` records both boolean investigative result and metadata (`info_targets`/`info_action`) so day emails can display a readable sentence such as "You tried to investigate players X and Y, and learned that neither is evil."
  - `Investigator` (replaces FirstWatcher): acts on the first night and receives a readable string message (e.g. "Investigation: one of 3 (Alice) or 5 (Eve) is possibly the Poisoner."). Investigator metadata (`info_targets`, `info_action`) is also recorded so day emails show the same readable sentence style the Fortune Teller uses.
  - Poisoning logic marks the victim with `poisoned` (the log reflects the poison victim, not the poisoner).

- Role assignment / player factory:
  - A canonical roster is kept stable for tests; runtime `setup_players()` can swap a canonical `Villager` into `Investigator` for live play so external expectations/tests remain stable.
  - A pool of good roles is preferred to fill canonical slots (Monk, Soldier, Fortune Teller, Investigator), extras become Villagers.

**Logging & diagnostics**
- Night resolution prints compact lines describing each role's action, e.g.:
  - "player [2] [Imp] tries to kill player(s) [4] and succeeds (dead, healthy)" — shows outcome and prior health flags.
  - "player [5] [Poisoner] poisons player [3] (Bob)" — deterministic poison log; poisoned flag stored on the victim.
  - Fortune Teller and Investigator lines show what they learned (and whether they were poisoned/inverted).

**Extending the project**
- Adding a new role:
 1. Update `utils/player_factory.py` to add the role to the pool and set appropriate `nightResponse`, `nightActionPriority`, and `first_night_only`/`skip_first_night` flags.
 2. Modify `utils/nightphase.py` `perform_night_actions` to handle the role's name in the resolution block (follow the style used for existing roles).
 3. If the role produces player-facing info, set `player['info_for_player']` and optionally `info_targets`/`info_action` for consistent daytime formatting.

- Using a real email backend:
 1. Provide IMAP/SMTP credentials via environment variables or a `.env` file (the codebase uses `python-dotenv`).
 2. Inspect `utils/email_handler.py` to see expected environment variable names and adjust as needed.
 3. For development, use `utils/demo_email_handler.py` and the `main.py` runner to simulate messages locally.

**Testing**
- Unit tests use `pytest` and live in `tests/`. Run `pytest -q` to run the test-suite. Tests currently exercise characters, role interactions and the day/night flows.

**Where to look next (recommended small improvements)**
- Add explicit unit tests for `Investigator` email delivery and format (currently the Investigator logic is implemented and carries metadata; tests would lock the readable sentence format).
- Improve target-list formatting to support more than two targets with commas and Oxford-style conjunctions.
- Add integration examples or a `docker-compose` setup if you plan to run with a real mailbox in CI or a staging environment.

---

If you'd like, I can:
- Add the `Investigator` unit tests under `tests/characters/` now, or
- Add example `.env.example` showing recommended IMAP/SMTP env vars, or
- Reformat the target-list wording to support arbitrary-length target lists.

Tell me which of the above you'd like next and I'll implement it.
