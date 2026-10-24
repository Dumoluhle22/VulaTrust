from datetime import date

import pytest

from app.reviews import (
    NEVER_REVIEWED, NO_NEXT_DATE, OVERDUE, SCHEDULED, is_review_overdue, review_status,
)

TODAY = date(2026, 10, 13)


@pytest.mark.parametrize(
    "last, nxt, status, overdue",
    [
        (None, None, NEVER_REVIEWED, True),
        (None, date(2027, 1, 1), NEVER_REVIEWED, True),   # planned, but never actually done
        (date(2026, 1, 1), date(2026, 10, 12), OVERDUE, True),   # yesterday
        (date(2026, 1, 1), date(2025, 1, 1), OVERDUE, True),     # long past
        (date(2026, 1, 1), date(2026, 10, 13), SCHEDULED, False),  # due today is not overdue
        (date(2026, 1, 1), date(2026, 10, 14), SCHEDULED, False),  # tomorrow
        (date(2026, 1, 1), date(2027, 6, 1), SCHEDULED, False),
        (date(2026, 1, 1), None, NO_NEXT_DATE, False),
    ],
)
def test_review_status_and_overdue(last, nxt, status, overdue):
    assert review_status(last, nxt, TODAY) == status
    assert is_review_overdue(last, nxt, TODAY) is overdue


def test_today_is_a_parameter_not_read_from_the_clock():
    last, nxt = date(2026, 1, 1), date(2026, 6, 1)
    assert is_review_overdue(last, nxt, date(2026, 5, 31)) is False
    assert is_review_overdue(last, nxt, date(2026, 6, 1)) is False
    assert is_review_overdue(last, nxt, date(2026, 6, 2)) is True
