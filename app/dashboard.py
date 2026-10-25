"""Numbers and lists for the dashboard (issues 18 and 19)."""
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import AgreementStatus, Application, TriState, Vendor
from app.reviews import NEVER_REVIEWED, OVERDUE, review_status
from app.scoring import ScoreResult, facts_from_vendor, score_vendor

TOP_COUNT = 5
INCOMPLETE_COUNT = 10


@dataclass(frozen=True)
class VendorRow:
    vendor: Vendor
    score: ScoreResult
    review: str


@dataclass
class Dashboard:
    vendor_count: int
    application_count: int
    unassigned_count: int
    level_counts: dict[str, int]
    top: list[VendorRow]
    no_agreement: list[VendorRow]
    overdue: list[VendorRow]
    no_owner: list[VendorRow]
    incomplete: list[VendorRow]


def build_dashboard(db: Session, today: date) -> Dashboard:
    vendors = db.scalars(select(Vendor).options(selectinload(Vendor.applications))).all()
    rows = [
        VendorRow(
            vendor,
            score_vendor(facts_from_vendor(vendor), today),
            review_status(vendor.last_reviewed, vendor.next_review_due, today),
        )
        for vendor in vendors
    ]
    name = lambda row: row.vendor.name.lower()

    level_counts = {"high": 0, "medium": 0, "low": 0}
    for row in rows:
        level_counts[row.score.level] += 1

    # Handles, or may handle, personal information but has no signed agreement.
    # Unknown stays in the list: missing information is not treated as safe.
    no_agreement = [
        r for r in rows
        if r.vendor.operator_agreement_status != AgreementStatus.SIGNED
        and r.vendor.handles_personal_info != TriState.NO
    ]
    overdue = [r for r in rows if r.review in (NEVER_REVIEWED, OVERDUE)]
    no_owner = [r for r in rows if not (r.vendor.owner and r.vendor.owner.strip())]
    incomplete = [r for r in rows if r.score.completeness.known < r.score.completeness.total]

    return Dashboard(
        vendor_count=len(rows),
        application_count=db.scalar(select(func.count(Application.id))) or 0,
        unassigned_count=db.scalar(
            select(func.count(Application.id)).where(Application.vendor_id.is_(None))
        ) or 0,
        level_counts=level_counts,
        top=sorted(rows, key=lambda r: (-r.score.score, name(r)))[:TOP_COUNT],
        no_agreement=sorted(no_agreement, key=lambda r: (-r.score.score, name(r))),
        # never-reviewed vendors first, then the longest overdue
        overdue=sorted(
            overdue,
            key=lambda r: (r.review != NEVER_REVIEWED, r.vendor.next_review_due or date.max, name(r)),
        ),
        no_owner=sorted(no_owner, key=lambda r: (-r.score.score, name(r))),
        # least complete first, then the riskiest
        incomplete=sorted(
            incomplete,
            key=lambda r: (r.score.completeness.known, -r.score.score, name(r)),
        )[:INCOMPLETE_COUNT],
    )
