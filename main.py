"""Simple CLI to create players and run one interactive round.

This script is a development helper that lets you quickly create a set of
players, start a round (messages are created and stored in MessageHandler),
and manually enter responses to simulate incoming emails. It's useful for
trying the orchestration without connecting real email.

Usage: run `python main.py` and follow the prompts.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
from utils.message_handler import MessageHandler
from game.controller import GameController


def prompt(prompt_text: str, default: str = "") -> str:
    v = input(f"{prompt_text} [{default}]: ").strip()
    return v if v else default


def main() -> None:
    load_dotenv()
    default_email = os.getenv("DEFAULT_PLAYER_EMAIL") or os.getenv("EMAIL_ADDRESS") or "player@example.com"

    print("Welcome to emailBOTC (interactive CLI).\n")

    while True:
        try:
            num_raw = input("Number of players: ").strip()
            num = int(num_raw)
            if num <= 0:
                print("Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("Please enter a valid integer.")

    players = []
    for i in range(1, num + 1):
        default_name = f"player{i}"
        name = prompt(f"Player {i} name", default_name)
        email = prompt(f"Player {i} email", default_email)
        # expected ints for this player (0-2)
        try:
            ei_raw = input(f"How many integers should {name} reply with? [0]: ").strip()
            expected_ints = int(ei_raw) if ei_raw else 0
            if expected_ints < 0:
                expected_ints = 0
            if expected_ints > 2:
                expected_ints = 2
        except ValueError:
            expected_ints = 0

        players.append({
            "playername": name,
            "player_email": email,
            "player_id": f"p{i}",
            "expected_ints": expected_ints,
        })

    mh = MessageHandler()
    gc = GameController(players, mh)

    print(f"\nCreated {len(players)} players:\n")
    for p in gc.registry.all_players():
        print(f" - {p.player_id}: {p.playername} <{p.player_email}> expected_ints={p.expected_ints}")

    while True:
        cmd = input("\nCommands: (s)tart round, (q)uit: ").strip().lower()
        if cmd in ("q", "quit"):
            print("Goodbye")
            return
        if cmd in ("s", "start"):
            prompt_text = input("Prompt text to send to players [Action]: ").strip() or "Action"
            try:
                req_raw = input("Override required_ints for all players? Enter 0/1/2 or leave blank: ").strip()
                required_ints = int(req_raw) if req_raw != "" else None
            except ValueError:
                required_ints = None

            batch_id = gc.start_round(prompt_text=prompt_text, required_ints=required_ints)
            print(f"Started round with batch_id: {batch_id}")

            # show round summary and enter player-centric respond UI
            print()
            print(f"Started round {batch_id}. You can inspect players and respond as if you are them.")

            # Player selection loop
            while True:
                players = list(gc.registry.all_players())
                print("\nPlayers:")
                for idx, p in enumerate(players, start=1):
                    cnt = len(mh.find_by_player(p.player_id))
                    print(f" {idx}) {p.playername} <{p.player_email}>  -- messages waiting: {cnt}")
                print(" D) Done responding for this round")

                choice = input("Choose a player number to inspect or D to finish: ").strip().lower()
                if choice in ("d", "done"):
                    break

                try:
                    sel = int(choice)
                    if sel < 1 or sel > len(players):
                        print("Invalid player number")
                        continue
                except ValueError:
                    print("Please enter a player number or D")
                    continue

                player = players[sel - 1]
                # show messages for this player
                while True:
                    pending = mh.find_by_player(player.player_id)
                    print(f"\nPlayer {player.playername} has {len(pending)} unresolved message(s).")
                    if not pending:
                        input("Press Enter to go back to player list...")
                        break

                    # list messages and let user pick one if multiple
                    print("Messages:")
                    for m_idx, m in enumerate(pending, start=1):
                        print(f" {m_idx}) Subject: {m.subject}  Required ints: {m.required_ints}  id:{m.id}")

                    mchoice = input("Select message number to open (or B to go back): ").strip().lower()
                    if mchoice in ("b", "back"):
                        break
                    try:
                        msel = int(mchoice)
                        if msel < 1 or msel > len(pending):
                            print("Invalid selection")
                            continue
                    except ValueError:
                        print("Enter a number or B to go back")
                        continue

                    msg = pending[msel - 1]
                    print(f"\n--- Message Content ---\nTo: {msg.to_email}\nSubject: {msg.subject}\nBody:\n{msg.body}\nRequired ints: {msg.required_ints}\n-----------------------")
                    action = input("(R)espond to this message, (C)lose player (go back to player select), or (B)ack: ").strip().lower()
                    if action in ("c", "close"):
                        # go back to player select
                        break
                    if action in ("b", "back"):
                        continue
                    if action in ("r", "respond"):
                        resp = input("Enter response body: ").strip()
                        ok = mh.resolve(msg.id, resp)
                        if ok:
                            print("Response accepted and message closed.")
                        else:
                            print("Response was invalid. A follow-up asking for correct format was created and pushed to the handler.")
                        # after responding, stay in the player's message view so the user can handle follow-ups
                        continue
                    print("Unknown option; returning to player messages")

            # After user finishes responding, show executed actions (GameController callback may have run)
            print("\nRound complete. Actions executed:")
            for a in gc.last_actions:
                print(f" - Actor {a.actor_id}: {a.kind} -> {a.payload}")

        else:
            print("Unknown command")


if __name__ == "__main__":
    main()
