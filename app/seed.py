"""Load the synthetic sample vendors into the database.

Usage:
    python -m app.seed

Safe to run more than once: vendors whose domain already exists are skipped.
"""
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import AgreementStatus, HostingLocation, TriState, Vendor

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "vendors.csv"


def _date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def load_vendors(db: Session, path: Path = DEFAULT_PATH) -> int:
    """Insert vendors from a CSV file. Returns how many were created."""
    created = 0
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            domain = row["primary_domain"] or None
            if domain and db.scalar(
                select(Vendor).where(Vendor.primary_domain == domain)
            ):
                continue
            db.add(
                Vendor(
                    name=row["name"],
                    primary_domain=domain,
                    owner=row["owner"] or None,
                    handles_personal_info=TriState(row["handles_personal_info"]),
                    data_types=row["data_types"] or None,
                    hosting_location=HostingLocation(row["hosting_location"]),
                    operator_agreement_status=AgreementStatus(
                        row["operator_agreement_status"]
                    ),
                    operator_agreement_date=_date(row["operator_agreement_date"]),
                    certifications=row["certifications"] or None,
                    last_reviewed=_date(row["last_reviewed"]),
                    next_review_due=_date(row["next_review_due"]),
                    notes=row["notes"] or None,
                )
            )
            created += 1
    db.commit()
    return created


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        created = load_vendors(db)
    print(f"Loaded {created} new vendors from {DEFAULT_PATH.name}")


if __name__ == "__main__":
    main()
