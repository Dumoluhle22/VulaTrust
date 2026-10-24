"""Review status for a vendor (issue 14). Pure functions: today is passed in."""
from datetime import date

NEVER_REVIEWED = "never_reviewed"
OVERDUE = "overdue"
SCHEDULED = "scheduled"
NO_NEXT_DATE = "no_next_date"

REVIEW_LABELS = {
    NEVER_REVIEWED: "Never reviewed",
    OVERDUE: "Overdue",
    SCHEDULED: "Scheduled",
    NO_NEXT_DATE: "Reviewed, but no next review date",
}


def review_status(last_reviewed: date | None, next_review_due: date | None, today: date) -> str:
    """Never reviewed, overdue, scheduled, or reviewed with no next date.

    A review due today is not overdue yet.
    """
    if last_reviewed is None:
        return NEVER_REVIEWED
    if next_review_due is None:
        return NO_NEXT_DATE
    return OVERDUE if next_review_due < today else SCHEDULED


def is_review_overdue(last_reviewed: date | None, next_review_due: date | None, today: date) -> bool:
    """True when the next review date has passed, or the vendor was never reviewed."""
    return review_status(last_reviewed, next_review_due, today) in (NEVER_REVIEWED, OVERDUE)
