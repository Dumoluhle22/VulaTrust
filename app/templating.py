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


templates.env.filters["pretty"] = pretty
templates.env.globals.update(
    TRISTATE_OPTIONS=TRISTATE_OPTIONS,
    HOSTING_OPTIONS=HOSTING_OPTIONS,
    AGREEMENT_OPTIONS=AGREEMENT_OPTIONS,
    SOURCE_OPTIONS=SOURCE_OPTIONS,
)
