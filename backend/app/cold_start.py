"""Cold start detection for Lambda."""

# Cold start detection - set True on module load, cleared after first request
_is_cold_start = True


def get_cold_start_status() -> bool:
    """Return True if this is the first request since Lambda cold start."""
    return _is_cold_start


def clear_cold_start() -> None:
    """Clear the cold start flag after first request."""
    global _is_cold_start
    _is_cold_start = False
