"""Database models for VulaTrust (issue 5).

Key design rule: safeguard fields allow yes / no / unknown, and the default is
UNKNOWN. A missing answer must never look like a safe answer.
"""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TriState(str, enum.Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class HostingLocation(str, enum.Enum):
    SOUTH_AFRICA = "south_africa"
    OUTSIDE_SOUTH_AFRICA = "outside_south_africa"
    UNKNOWN = "unknown"


class AgreementStatus(str, enum.Enum):
    NONE = "none"
    REQUESTED = "requested"
    SIGNED = "signed"
    UNKNOWN = "unknown"


class ApplicationSource(str, enum.Enum):
    MANUAL = "manual"
    CSV = "csv"
    GOOGLE = "google"
    MICROSOFT = "microsoft"


def _enum_column(enum_cls: type[enum.Enum]) -> Enum:
    """Store the enum's value (e.g. 'unknown'), as a plain string column."""
    return Enum(
        enum_cls,
        values_callable=lambda e: [member.value for member in e],
        native_enum=False,
        validate_strings=True,
        length=32,
    )


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # Unique so that domain matching can never be ambiguous. NULL is allowed.
    primary_domain: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    owner: Mapped[str | None] = mapped_column(String(200))

    handles_personal_info: Mapped[TriState] = mapped_column(
        _enum_column(TriState), default=TriState.UNKNOWN
    )
    data_types: Mapped[str | None] = mapped_column(Text)
    hosting_location: Mapped[HostingLocation] = mapped_column(
        _enum_column(HostingLocation), default=HostingLocation.UNKNOWN
    )
    operator_agreement_status: Mapped[AgreementStatus] = mapped_column(
        _enum_column(AgreementStatus), default=AgreementStatus.UNKNOWN
    )
    operator_agreement_date: Mapped[date | None] = mapped_column(Date)
    certifications: Mapped[str | None] = mapped_column(Text)

    last_reviewed: Mapped[date | None] = mapped_column(Date)
    next_review_due: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # passive_deletes lets the database apply ON DELETE SET NULL, so deleting a
    # vendor leaves its applications behind as "unassigned".
    applications: Mapped[list["Application"]] = relationship(
        back_populates="vendor", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Vendor id={self.id} name={self.name!r}>"


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    source: Mapped[ApplicationSource] = mapped_column(
        _enum_column(ApplicationSource), default=ApplicationSource.CSV
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    unassigned_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)

    applications: Mapped[list["Application"]] = relationship(
        back_populates="import_batch", passive_deletes=True
    )


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint("user_count >= 0", name="ck_applications_user_count"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))

    # Nullable on purpose: no vendor means "unassigned".
    vendor_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendors.id", ondelete="SET NULL"), index=True
    )
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL")
    )

    source: Mapped[ApplicationSource] = mapped_column(
        _enum_column(ApplicationSource), default=ApplicationSource.MANUAL
    )
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    user_count: Mapped[int] = mapped_column(Integer, default=0)
    scopes: Mapped[str | None] = mapped_column(Text)
    privileged: Mapped[TriState] = mapped_column(
        _enum_column(TriState), default=TriState.UNKNOWN
    )
    # How the vendor link was made, e.g. "exact_domain" or "manual" (issue 10).
    match_method: Mapped[str | None] = mapped_column(String(50))

    vendor: Mapped["Vendor | None"] = relationship(back_populates="applications")
    import_batch: Mapped["ImportBatch | None"] = relationship(
        back_populates="applications"
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} name={self.name!r}>"
