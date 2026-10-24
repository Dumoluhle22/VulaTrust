"""One place to ask "what is today's date?", so tests can fix it."""
from datetime import date


def today() -> date:
    return date.today()
