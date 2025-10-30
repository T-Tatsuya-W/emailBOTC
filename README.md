# emailBOTC

Run tests:

```powershell
python -m pytest -q
```

Overview
--------
emailBOTC is a small framework to run an email-driven game loop (think social deduction
games where each player receives an email prompt, responds, and the server collects
and resolves actions). The repo currently contains:

- A minimal `Player` model (`game/player.py`) storing identity and state.
- An `EmailHandler` utility (`utils/email_handler.py`) with send/receive primitives.
- A `Message` + `MessageHandler` (`utils/message_handler.py`) that tracks outstanding
  messages waiting for replies and validates/resolves responses.
- Unit tests exercising the message handling and player integration.

Design goals and flow
---------------------
The high-level flow we want to implement:

1. The `GameController` constructs all `Player` objects and registers them.
2. For each round the controller sends a prompt to each player (via `EmailHandler`),
   constructing `Message` objects and adding them to `MessageHandler` (batch-tagging
   them if they belong to the same round).
3. Players reply by email. `EmailHandler` receives incoming emails and hands them to
   `MessageHandler.resolve(...)` which validates the response (e.g. required number
   of integers) and marks messages resolved.
4. When all messages for the round's batch are resolved, `MessageHandler` invokes a
   registered batch callback. That callback converts message responses into `Action`
   instances and hands the list to the `GameController`.
5. `GameController` executes the actions (mutating player state), gathers results,
   and optionally begins the next round (possibly sending a different prompt text).

Major components and responsibilities
-------------------------------------

- Player (`game.player.Player`)
  - Holds identity (player_id, name, email) and state (alive, can_vote, expected_ints, etc.).
  - Can create/send `Message`s into a `MessageHandler` (via `send_message`).

- Message & MessageHandler (`utils.message_handler`)
  - `Message`: data container with `required_ints`, optional `batch_id`, `player_id`, etc.
  - `MessageHandler`: stores unresolved messages, supports resolving messages (with
    validation), re-opening on invalid responses, registering batch callbacks and
    firing them when all messages in a batch are resolved.

- EmailHandler (`utils.email_handler.EmailHandler`)
  - Low-level send/receive. Responsible for polling IMAP and producing incoming
    message payloads (from, subject, body). Will be wired to call into
    `MessageHandler.resolve()`.

- GameController (`game.controller.GameController`) - planned
  - Orchestrates player creation, batch prompting, conversion from responses to
    `Action` classes, executing actions, updating state, and repeating the loop.

- PlayerRegistry (utility)
  - Maps `player_id` -> `Player` instance for routing results back to players.

Data shapes / Contracts
-----------------------

- Message:
  - player_id: str
  - to_email: str
  - subject: str
  - body: str
  - required_ints: int (0,1,2)
  - batch_id: Optional[str]

- Action (planned):
  - actor_id: str
  - kind: str
  - payload: dict

Validation rules
----------------

- `MessageHandler.resolve(message_id, response, reopen_on_invalid=False)`
  - Validates response matches `required_ints` by extracting integers from `response`.
  - Accepts (resolves) only when the count matches. If `reopen_on_invalid` is True,
    it closes the invalid message and creates a fresh one with the same params.
  - When a message belonging to a `batch_id` is resolved, the handler checks whether
    all messages for that batch are resolved and calls the registered batch callback.

Gaps and next steps (prioritized)
---------------------------------

1. GameController skeleton (high priority)
   - Implement `game/controller.py` that:
     - Accepts a list of player configs, creates `Player` instances and registers
       them with a `PlayerRegistry`.
     - Sends batch prompts (creating `Message`s with `batch_id`) and registers
       a callback with `MessageHandler` for that batch.
     - On batch callback: converts resolved messages into `Action` objects and
       executes them.

2. PlayerRegistry (high priority)
   - Simple singleton / object that maps `player_id` -> `Player` and provides
     `get(player_id)` and `register(player)`.

3. Wire EmailHandler -> MessageHandler (mid priority)
   - Implement a small adapter that polls IMAP via `EmailHandler._fetch_unseen_messages()`
     and calls `MessageHandler.resolve(...)` for matching subject + from; this
     adapter will run in a loop or background task.

4. Define `Action` classes and conversion logic (mid priority)
   - Convert responses (validated integers) into domain Actions (attack, protect, nominate, etc.)
   - Ensure deterministic ordering when converting to actions if needed.

5. Integration tests and examples (high priority)
   - End-to-end tests that simulate players, the message round, resolution, action
     conversion, and game state updates.

6. Concurrency, persistence, and error handling (low / later)
   - Make MessageHandler thread-safe if responses are processed by multiple threads.
   - Persist outstanding messages for crash-recovery (e.g., simple JSON file).
   - Add timeouts and retries when waiting for responses.

Testing checklist
-----------------

- Unit tests already added for `MessageHandler` behavior (LIFO, resolve, reopen,
  batch callback). Add additional tests for:
  - `GameController` round lifecycle (send -> collect -> convert -> execute).
  - `PlayerRegistry` registration + lookup.
  - EmailAdapter: mapping incoming email payloads to message resolution.
  - Action conversion: correct mapping of integer replies to actions.

Example sequence (simplified)
-----------------------------

1. GameController sends batch "round-001" prompting all players for 2 integers.
2. For each player GameController calls player.send_message(..., required_ints=2, batch_id="round-001").
3. MessageHandler holds all messages and `register_callback("round-001", cb)`.
4. EmailAdapter polls incoming messages and calls MessageHandler.resolve(message_id, response).
5. When all messages in batch are resolved, `cb` receives the list; it converts
   responses into `Action` objects and passes them to GameController.execute(actions).

How you can help / what I can implement next
--------------------------------------------

- I can implement the `GameController` skeleton and `PlayerRegistry` next (recommended).
- Or I can wire the `EmailHandler` to the `MessageHandler` with an adapter that
  can be run in the background to process incoming emails.

If you want, I will implement the `GameController` and unit tests for the full
round flow next. That will make it easy to iterate on action conversion and
integration with the email adapter.




# Rough notes for me

test with command 

```python -m pytest -q```

BOTC

Player class 
Must keep their own role name. Their name and email for routing. 
Must have functions to send public emails to each. These may have overrides or adding for each player. 


Standard needs to send info. With ability to add or remove information. 
Perhaps a global class to write updates. And to handle actions. 

Actions fetched will be the output of the player fetches. 

They need to async wait and fetch emails. But the subsequent code must wait for all in order to progress. 

Each player should return an “action” class that describes what needs to happen. Each of these are aggregated into a handler that will go in the correct order to accommodate some dependencies. 



All the drunk poison and misleading information could be coherent. 

Given each evil will be given a specific role to faint. We can construct two player allocation sets. A simple dictionary or something. Player ID and roles. 
A truth one for referring to for most cases. 

Some roles need to keep track of one specific player as their red herring etc. 
would these be a seperate set of dicts?

The emails that require input will be the only needing potential validation or back and forth. Rest are purely inform. 

Later will need to add the case for day noms and votes. 

For now only night considered. 


Each role adds overrides to t player. 
Some players. Need to be given specific information or be promoted for information. 

Their email and ack should wait for appropriate responses in this case. 

Some are promoted for actions at night. And some are actioned. Some are information returned in the morning. 

This is the format for most classes. 




Some have special actions.  Leave these for now. 





To add day. 
Need to allow to check for nomination emails. 

Day emails should check for either a valid nomination format or ignore. 

Nomination emails should then announce to all that they have been noninated. Then prompt the nominated to respond, again public ally sent. After which votes emails. Requiring valid response from all. 

After a voting round is run. We can announce with the same rules as for the initial day mail. Allowing for further nominations. But otherwise waiting for all to ack and move into night. 

Night starts with an end of day  notification. Sent to all update on current state and prompt the characters with actions for the response. Then those go back to the morning mail for a response.





