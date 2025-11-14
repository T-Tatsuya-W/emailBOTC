"""Lightweight dotenv loader used for local development/tests when
`python-dotenv` is not installed. This reads a `.env` file from the
project root (one directory above this package) and sets the variables
into `os.environ`.

The function returns True if a `.env` file was found and parsed,
otherwise False. This is intentionally minimal and not a full
replacement for python-dotenv; it supports simple KEY=VALUE lines and
ignores comments and blank lines.
"""

import os


def load_dotenv(path: str | None = None) -> bool:
    if path is None:
        # project root is the parent directory of this package
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        path = os.path.join(root, ".env")

    try:
        if not os.path.exists(path):
            return False

        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # Only set if not already present to preserve real env vars
                os.environ.setdefault(key, val)
        return True
    except Exception:
        return False
