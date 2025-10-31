"""Simple interactive test harness for utils.email_handler.EmailHandler.

Usage: run `python main.py` and follow the prompts. Make sure your `.env`
contains the required variables (EMAIL_ADDRESS, EMAIL_APP_PASSWORD, SMTP_SERVER,
IMAP_SERVER, etc.).
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from utils.email_handler import EmailHandler


def show_config() -> None:
    # show non-sensitive config to help debugging
    print("Detected configuration:")
    print("  EMAIL_ADDRESS:", os.getenv("EMAIL_ADDRESS"))
    print("  SMTP_SERVER:", os.getenv("SMTP_SERVER"))
    print("  SMTP_PORT:", os.getenv("SMTP_PORT"))
    print("  IMAP_SERVER:", os.getenv("IMAP_SERVER"))
    print("  IMAP_PORT:", os.getenv("IMAP_PORT"))


def prompt(prompt_text: str, default: Optional[str] = None) -> str:
    if default:
        raw = input(f"{prompt_text} [{default}]: ")
        return raw.strip() or default
    else:
        return input(f"{prompt_text}: ").strip()


def main() -> None:
    print("EmailHandler test harness")
    show_config()

    eh = EmailHandler()

    while True:
        print()
        print("Options:")
        print("  1) Send email")
        print("  2) List unread messages")
        print("  q) Quit")
        choice = input("Choose: ").strip().lower()

        if choice == "1":
            to_addr = prompt("To address", os.getenv("EMAIL_ADDRESS"))
            subject = prompt("Subject", "Test from EmailHandler")
            reply_id_str = prompt("(Optional) Thread ID (integer) to thread this message", "").strip() or None
            reply_id = None
            if reply_id_str:
                try:
                    reply_id = int(reply_id_str)
                except ValueError:
                    print("Invalid thread id input; ignoring and sending as new message.")
                    reply_id = None
            print("Enter body. Finish with an empty line.")
            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if line == "":
                    break
                lines.append(line)
            body = "\n".join(lines) or "Hello from EmailHandler!"
            try:
                ok = eh.send_email(to_addr, subject, body, thread_id=reply_id)
                print("send_email returned:", ok)
            except Exception as e:
                print("Error sending email:", e)

        elif choice == "2":
            try:
                msgs = eh.check_unread()
                if not msgs:
                    print("No unread messages.")
                else:
                    print(f"{len(msgs)} unread message(s):")
                    for m in msgs:
                        print("- id:", m.get("id"), " uid:", m.get("uid"))
                        print("  from:", m.get("from"))
                        print("  subject:", m.get("subject"))
                        print("  date:", m.get("date"))
                        print("  body:\n", m.get("clean_body") or m.get("body") or "")
                        print("  ----")
            except Exception as e:
                print("Error checking unread:", e)

        elif choice == "q":
            print("Goodbye")
            return
        
        else:
            print("Unknown choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
