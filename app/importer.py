"""Plan and save an import (issues 10 and 11).

build_plan() decides what WOULD happen, changing nothing. apply_import() saves
it in a single transaction: either every row is saved or none is.

Re-import rules:
* The same application is recognised by app name (ignoring case), the cleaned
  domain from the file, and the source.
* A re-import updates users, access and privileged from the file.
* A vendor link a person made by hand is never changed by an import.
* Only applications that came from an earlier import are updated. Hand-entered
  applications are left alone.
"""
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.csv_import import CsvCheckResult, ParsedRow
from app.matching import MatchResult, VendorMatcher
from app.models import Application, ApplicationSource, ImportBatch, Vendor

MANUAL = "manual"


def application_key(name: str, domain: str | None, source: str) -> tuple[str, str, str]:
    return (name.strip().lower(), domain or "", source)


@dataclass
class PlannedRow:
    row: ParsedRow
    match: MatchResult
    existing_id: int | None = None  # set when this row updates an earlier import


@dataclass
class ImportPlan:
    result: CsvCheckResult
    rows: list[PlannedRow] = field(default_factory=list)
    vendor_names: dict[int, str] = field(default_factory=dict)

    @property
    def matched(self) -> int:
        return sum(1 for item in self.rows if item.match.vendor_id is not None)

    @property
    def unassigned(self) -> int:
        return len(self.rows) - self.matched

    @property
    def to_update(self) -> int:
        return sum(1 for item in self.rows if item.existing_id is not None)

    @property
    def to_create(self) -> int:
        return len(self.rows) - self.to_update


def build_plan(db: Session, result: CsvCheckResult) -> ImportPlan:
    vendors = db.execute(select(Vendor.id, Vendor.name, Vendor.primary_domain)).all()
    matcher = VendorMatcher([(v.id, v.primary_domain) for v in vendors])

    earlier: dict[tuple[str, str, str], Application] = {}
    for application in db.scalars(
        select(Application)
        .where(Application.import_batch_id.is_not(None))
        .order_by(Application.id)
    ):
        key = application_key(application.name, application.source_domain, application.source.value)
        earlier.setdefault(key, application)

    plan = ImportPlan(result=result, vendor_names={v.id: v.name for v in vendors})
    for row in result.valid:
        existing = earlier.get(application_key(row.app_name, row.vendor_domain, row.source.value))
        if existing is not None and existing.match_method == MANUAL and existing.vendor_id:
            match = MatchResult(existing.vendor_id, MANUAL)  # a person's link wins
        else:
            match = matcher.match(row.vendor_domain)
        plan.rows.append(PlannedRow(row, match, existing.id if existing else None))
    return plan


def _write_row(db: Session, batch: ImportBatch, item: PlannedRow) -> bool:
    """Create or update one application. Returns True if it was created."""
    row, match = item.row, item.match
    if item.existing_id is not None:
        application = db.get(Application, item.existing_id)
        application.name = row.app_name
        application.user_count = row.user_count
        application.scopes = row.scopes
        application.privileged = row.privileged
        application.import_batch_id = batch.id
        if application.match_method != MANUAL:
            application.vendor_id = match.vendor_id
            application.match_method = match.method
        return False
    db.add(
        Application(
            name=row.app_name,
            vendor_id=match.vendor_id,
            import_batch_id=batch.id,
            source=ApplicationSource(row.source),
            user_count=row.user_count,
            scopes=row.scopes,
            privileged=row.privileged,
            match_method=match.method,
            source_domain=row.vendor_domain,
        )
    )
    return True


def apply_import(db: Session, filename: str, plan: ImportPlan) -> ImportBatch:
    """Save the plan as one import batch. All rows are saved, or none."""
    result = plan.result
    batch = ImportBatch(
        filename=filename[:255],
        source=ApplicationSource.CSV,
        row_count=result.rows_read,
        matched_count=plan.matched,
        unassigned_count=plan.unassigned,
        rejected_count=len(result.rejected),
        duplicate_count=len(result.duplicates),
    )
    try:
        db.add(batch)
        db.flush()  # gives the batch an id without committing
        created = updated = 0
        for item in plan.rows:
            if _write_row(db, batch, item):
                created += 1
            else:
                updated += 1
        batch.created_count = created
        batch.updated_count = updated
        db.commit()
    except Exception:
        db.rollback()
        raise
    return batch
