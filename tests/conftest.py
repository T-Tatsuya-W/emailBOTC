def pytest_collection_modifyitems(items):
<<<<<<< Updated upstream
    """Replace test display name with the first line of the test function's
    docstring when present, so test output reads like plain English sentences.
    """
    for item in items:
        func = getattr(item, "function", None)
        if func is None:
            continue
        doc = func.__doc__
        if not doc:
            continue
        name = doc.strip().splitlines()[0]
        # Set a friendly display name and adjust the nodeid so pytest prints it
        item.name = name
        parts = item.nodeid.split("::")
        parts[-1] = name
        item._nodeid = "::".join(parts)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

=======
    # No-op: legacy hook removed. This stub remains to avoid modifying nodeids.
    return
>>>>>>> Stashed changes
