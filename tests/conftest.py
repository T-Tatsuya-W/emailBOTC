def pytest_collection_modifyitems(items):
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
