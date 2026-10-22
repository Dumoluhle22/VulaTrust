"""Check an uploaded CSV of applications (issue 9).

This module only READS and CHECKS. It never saves anything, and it never runs
or evaluates anything found in the file: cells are treated as plain text.

Matching rows to vendors and saving them come later (issues 10 and 11).
"""
import csv
import io
import re
from dataclasses import dataclass, field

from app.domains import is_valid_domain, normalise_domain
from app.models import ApplicationSource, TriState
from app.schemas import MAX_NAME_LENGTH, MAX_SCOPES_LENGTH, MAX_USER_COUNT

MAX_FILE_BYTES = 1_048_576  # 1 MB
MAX_ROWS = 5_000
REQUIRED_COLUMNS = ["app_name", "vendor_domain", "source", "user_count", "scopes", "privileged"]
ALLOWED_SOURCES = [member.value for member in ApplicationSource]
ALLOWED_PRIVILEGED = [member.value for member in TriState]
# A spreadsheet treats a cell starting with one of these as a formula.
FORMULA_STARTS = ("=", "+", "-", "@")
DISPLAY_LENGTH = 80


@dataclass
class ParsedRow:
    line: int
    app_name: str
    vendor_domain: str | None  # cleaned; None means unassigned
    source: ApplicationSource
    user_count: int
    scopes: str | None
    privileged: TriState
    warnings: list[str] = field(default_factory=list)


@dataclass
class RejectedRow:
    line: int
    app_name: str  # shortened for display
    reasons: list[str]


@dataclass
class DuplicateRow:
    line: int
    app_name: str
    first_line: int


@dataclass
class CsvCheckResult:
    file_error: str | None = None
    rows_read: int = 0
    blank_rows: int = 0
    valid: list[ParsedRow] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)
    duplicates: list[DuplicateRow] = field(default_factory=list)

    @property
    def warnings(self) -> list[tuple[int, str]]:
        return [(row.line, text) for row in self.valid for text in row.warnings]


def neutralise_formula(text: str) -> tuple[str, bool]:
    """Prefix an apostrophe so a spreadsheet will not treat the text as a formula."""
    if text.startswith(FORMULA_STARTS):
        return "'" + text, True
    return text, False


def _shorten(text: str) -> str:
    return text if len(text) <= DISPLAY_LENGTH else text[: DISPLAY_LENGTH - 1] + "…"


def _file_error(result: CsvCheckResult, message: str) -> CsvCheckResult:
    result.file_error = message
    return result


def check_csv(data: bytes, filename: str | None = None) -> CsvCheckResult:
    """Validate a CSV file's bytes. Returns everything found; saves nothing."""
    result = CsvCheckResult()

    if filename is not None and not filename.lower().endswith(".csv"):
        return _file_error(result, "Only .csv files are accepted.")
    if len(data) > MAX_FILE_BYTES:
        return _file_error(
            result, f"The file is too large (maximum {MAX_FILE_BYTES // 1_048_576} MB)."
        )
    if not data.strip():
        return _file_error(result, "The file is empty.")
    if b"\x00" in data:
        return _file_error(result, "This does not look like a text CSV file.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return _file_error(
            result,
            "The file is not UTF-8 text. In Excel, choose Save As and then CSV UTF-8.",
        )

    # Some regional Excel settings (including common South African ones) use ";".
    first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)

    header: list[str] | None = None
    try:
        for raw in reader:
            if any(cell.strip() for cell in raw):
                header = [cell.strip().lower() for cell in raw]
                break
    except csv.Error as exc:
        return _file_error(result, f"Could not read the file: {exc}")
    if header is None:
        return _file_error(result, "The file is empty.")

    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        return _file_error(
            result,
            f"Missing required columns: {', '.join(missing)}. "
            f"The first row must contain: {', '.join(REQUIRED_COLUMNS)}.",
        )
    index = {name: header.index(name) for name in REQUIRED_COLUMNS}

    first_seen: dict[tuple[str, str, str], int] = {}
    while True:
        line = reader.line_num + 1  # the line this record starts on
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            return _file_error(result, f"Could not read the file near line {line}: {exc}")

        if not any(cell.strip() for cell in row):
            result.blank_rows += 1
            continue
        result.rows_read += 1
        if result.rows_read > MAX_ROWS:
            return _file_error(
                result, f"The file has more than {MAX_ROWS:,} rows. Split it into smaller files."
            )

        if len(row) != len(header):
            result.rejected.append(
                RejectedRow(
                    line,
                    _shorten(row[0].strip()) if row else "",
                    [
                        f"Expected {len(header)} columns but found {len(row)}. "
                        "A value containing a comma needs to be wrapped in quotes."
                    ],
                )
            )
            continue

        parsed, reasons = _check_row(row, index, line)
        if reasons:
            result.rejected.append(
                RejectedRow(line, _shorten(row[index["app_name"]].strip()), reasons)
            )
            continue

        key = (parsed.app_name.lower(), parsed.vendor_domain or "", parsed.source.value)
        if key in first_seen:
            result.duplicates.append(DuplicateRow(line, parsed.app_name, first_seen[key]))
            continue
        first_seen[key] = line
        result.valid.append(parsed)

    return result


def _check_row(row: list[str], index: dict[str, int], line: int):
    """Return (ParsedRow, []) or (None, [reasons...]). Collects every problem."""
    cell = {name: row[pos].strip() for name, pos in index.items()}
    reasons: list[str] = []
    warnings: list[str] = []

    name = cell["app_name"]
    if not name:
        reasons.append("App name is required.")
    elif len(name) > MAX_NAME_LENGTH:
        reasons.append(f"App name is too long (maximum {MAX_NAME_LENGTH} characters).")

    source_text = cell["source"].lower() or ApplicationSource.CSV.value
    if source_text not in ALLOWED_SOURCES:
        reasons.append(f"Source must be one of: {', '.join(ALLOWED_SOURCES)}.")

    count_text = cell["user_count"] or "0"
    user_count = 0
    if re.fullmatch(r"[0-9]+", count_text):
        user_count = int(count_text)
        if user_count > MAX_USER_COUNT:
            reasons.append(f"User count must be {MAX_USER_COUNT:,} or less.")
    elif re.fullmatch(r"-[0-9]+", count_text):
        reasons.append("User count must be 0 or more.")
    else:
        reasons.append("User count must be a whole number.")

    privileged_text = cell["privileged"].lower() or TriState.UNKNOWN.value
    if privileged_text not in ALLOWED_PRIVILEGED:
        reasons.append("Privileged must be yes, no or unknown.")

    scopes = cell["scopes"]
    if len(scopes) > MAX_SCOPES_LENGTH:
        reasons.append(
            f"Access description is too long (maximum {MAX_SCOPES_LENGTH} characters)."
        )

    if reasons:
        return None, reasons

    name, changed = neutralise_formula(name)
    if changed:
        warnings.append("App name started with a formula character, so an apostrophe was added.")
    scopes, changed = neutralise_formula(scopes)
    if changed:
        warnings.append("Access description started with a formula character, so an apostrophe was added.")

    domain: str | None = None
    if cell["vendor_domain"]:
        cleaned = normalise_domain(cell["vendor_domain"])
        if is_valid_domain(cleaned):
            domain = cleaned
        else:
            warnings.append(
                f"Domain '{_shorten(cell['vendor_domain'])}' is not valid, "
                "so the application will be left unassigned."
            )

    return (
        ParsedRow(
            line=line,
            app_name=name,
            vendor_domain=domain,
            source=ApplicationSource(source_text),
            user_count=user_count,
            scopes=scopes or None,
            privileged=TriState(privileged_text),
            warnings=warnings,
        ),
        [],
    )
