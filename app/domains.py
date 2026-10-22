"""Domain clean-up and validation.

Shared by the vendor form (issue 6) and, later, CSV matching (issue 10), so the
same text is always treated the same way.
"""
import re

_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")
_DOMAIN = re.compile(
    r"^(?=.{1,255}$)"
    r"([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$"
)


def normalise_domain(raw: str) -> str:
    """Lowercase; drop protocol, path, query, port, login part and leading www."""
    value = raw.strip().lower()
    value = _SCHEME.sub("", value)
    value = re.split(r"[/?#]", value, maxsplit=1)[0]
    value = value.rsplit("@", 1)[-1]
    value = value.split(":", 1)[0]
    value = value.removeprefix("www.")
    return value.rstrip(".")


def is_valid_domain(domain: str) -> bool:
    """True for names like paytrack.example. Rejects localhost, spaces, IPs."""
    if not _DOMAIN.match(domain):
        return False
    return not domain.rsplit(".", 1)[-1].isdigit()
