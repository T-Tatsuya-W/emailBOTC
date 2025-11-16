"""Central configuration for polling timings used by message handling.

Set `DEFAULT_POLL_EVERY` (seconds between polls) and `DEFAULT_POLL_FOR`
(total seconds to poll) here so they're easy to change in one place.

Note: callers may override these by passing explicit values to
`send_and_resolve_all` or `get_night_actions`.
"""

# Seconds between polling attempts
DEFAULT_POLL_EVERY = 5

# Total seconds to poll before giving up
DEFAULT_POLL_FOR = 60 * 1
