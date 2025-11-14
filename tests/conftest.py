import sys
from pathlib import Path

# Minimal conftest: ensure project root is on sys.path for imports.
# No pytest_collection_modifyitems hook so pytest uses default function names.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
