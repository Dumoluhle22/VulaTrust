"""Pydantic validation for vendor form input (issue 6)."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains import is_valid_domain, normalise_domain
from app.models import AgreementStatus, ApplicationSource, HostingLocation, TriState


# Limits shared by the application form and the CSV check.
MAX_NAME_LENGTH = 200
MAX_SCOPES_LENGTH = 500
MAX_USER_COUNT = 1_000_000


class VendorForm(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    primary_domain: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=200)
    handles_personal_info: TriState = TriState.UNKNOWN
    data_types: str | None = Field(default=None, max_length=1000)
    hosting_location: HostingLocation = HostingLocation.UNKNOWN
    operator_agreement_status: AgreementStatus = AgreementStatus.UNKNOWN
    operator_agreement_date: date | None = None
    certifications: str | None = Field(default=None, max_length=500)
    last_reviewed: date | None = None
    next_review_due: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("primary_domain")
    @classmethod
    def clean_domain(cls, value: str | None) -> str | None:
        if value is None:
            return None
        domain = normalise_domain(value)
        if not is_valid_domain(domain):
            raise ValueError("Enter a valid domain, for example paytrack.example.")
        return domain


class ApplicationForm(BaseModel):
    """Validation for the application form (issue 7)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    vendor_id: int | None = None
    source: ApplicationSource = ApplicationSource.MANUAL
    user_count: int = Field(default=0, ge=0, le=MAX_USER_COUNT)
    scopes: str | None = Field(default=None, max_length=MAX_SCOPES_LENGTH)
    privileged: TriState = TriState.UNKNOWN


def validate_vendor_dates(form: "VendorForm", today: date) -> dict[str, str]:
    """Cross-field date rules (issues 13 and 14). Returns errors keyed by field."""
    errors: dict[str, str] = {}

    signed = form.operator_agreement_status == AgreementStatus.SIGNED
    if signed and form.operator_agreement_date is None:
        errors["operator_agreement_date"] = "Enter the date the agreement was signed."
    elif form.operator_agreement_date is not None and not signed:
        errors["operator_agreement_date"] = (
            "Only enter a date when the agreement is signed. Clear it, or set the status to Signed."
        )
    elif form.operator_agreement_date is not None and form.operator_agreement_date > today:
        errors["operator_agreement_date"] = "The signing date cannot be in the future."

    if form.last_reviewed is not None and form.last_reviewed > today:
        errors["last_reviewed"] = "Last reviewed cannot be in the future."
    if (
        form.last_reviewed is not None
        and form.next_review_due is not None
        and form.next_review_due < form.last_reviewed
    ):
        errors["next_review_due"] = "Next review due cannot be before the last review."
    return errors
