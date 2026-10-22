"""Small helpers shared by the form screens."""
from fastapi import Request
from pydantic import ValidationError


async def read_form(request: Request, fields: list[str]) -> dict[str, str]:
    form = await request.form()
    return {field: str(form.get(field) or "") for field in fields}


def values_from_object(obj, fields: list[str]) -> dict[str, str]:
    """Turn a database object into the strings an edit form shows."""
    values = {}
    for field in fields:
        raw = getattr(obj, field)
        if raw is None:
            values[field] = ""
        elif hasattr(raw, "isoformat"):
            values[field] = raw.isoformat()
        else:
            values[field] = str(getattr(raw, "value", raw))
    return values


def error_messages(exc: ValidationError) -> dict[str, str]:
    """Turn Pydantic errors into short, readable messages keyed by field."""
    messages: dict[str, str] = {}
    for err in exc.errors():
        field = str(err["loc"][0]) if err["loc"] else "form"
        if field in messages:
            continue
        kind = err["type"]
        if kind in ("missing", "string_too_short"):
            text = "This field is required."
        elif kind == "string_too_long":
            text = f"Too long (maximum {err['ctx']['max_length']} characters)."
        elif kind == "int_parsing":
            # A vendor_id that is not a number can only come from a tampered form.
            text = (
                "Choose a vendor from the list."
                if field == "vendor_id"
                else "Enter a whole number."
            )
        elif kind == "greater_than_equal":
            text = f"Must be {err['ctx']['ge']} or more."
        elif kind == "less_than_equal":
            text = f"Must be {err['ctx']['le']} or less."
        elif kind.startswith("enum"):
            text = "Choose one of the listed options."
        elif kind.startswith("date"):
            text = "Enter a valid date (YYYY-MM-DD)."
        elif kind == "value_error":
            text = str(err["ctx"]["error"])
        else:
            text = err["msg"]
        messages[field] = text
    return messages
