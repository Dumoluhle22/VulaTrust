"""Shared Jinja2 setup, so routes and main.py use the same templates."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

TRISTATE_OPTIONS = [("yes", "Yes"), ("no", "No"), ("unknown", "Unknown")]
HOSTING_OPTIONS = [
    ("south_africa", "South Africa"),
    ("outside_south_africa", "Outside South Africa"),
    ("unknown", "Unknown"),
]
AGREEMENT_OPTIONS = [
    ("none", "None"),
    ("requested", "Requested"),
    ("signed", "Signed"),
    ("unknown", "Unknown"),
]
SOURCE_OPTIONS = [
    ("manual", "Added manually"),
    ("csv", "CSV import"),
    ("google", "Google Workspace"),
    ("microsoft", "Microsoft 365"),
]

_LABELS = dict(TRISTATE_OPTIONS + HOSTING_OPTIONS + AGREEMENT_OPTIONS + SOURCE_OPTIONS)


def pretty(value) -> str:
    """Turn an enum or stored value into display text. Unknown stays visible."""
    raw = getattr(value, "value", value)
    return _LABELS.get(raw, str(raw))


_MATCH_LABELS = {
    "exact_domain": "Exact domain",
    "subdomain": "Subdomain",
    "manual": "Linked manually",
}


def match_label(value) -> str:
    """Say how an application was linked to its vendor."""
    return _MATCH_LABELS.get(value, "Not linked")


templates.env.filters["pretty"] = pretty
templates.env.filters["match_label"] = match_label
templates.env.globals.update(
    TRISTATE_OPTIONS=TRISTATE_OPTIONS,
    HOSTING_OPTIONS=HOSTING_OPTIONS,
    AGREEMENT_OPTIONS=AGREEMENT_OPTIONS,
    SOURCE_OPTIONS=SOURCE_OPTIONS,
)
