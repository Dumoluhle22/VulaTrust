"""Vendor screens: list, add, edit, delete (issue 6)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import clock
from app.database import get_db
from app.formutils import error_messages, read_form, values_from_object
from app.messages import MESSAGES
from app.models import Application, Vendor
from app.reviews import review_status
from app.schemas import VendorForm, validate_vendor_dates
from app.scoring import facts_from_vendor, score_vendor
from app.templating import templates

router = APIRouter()

FORM_FIELDS = [
    "name", "primary_domain", "owner", "handles_personal_info", "data_types",
    "hosting_location", "operator_agreement_status", "operator_agreement_date",
    "certifications", "last_reviewed", "next_review_due", "notes",
]
ENUM_FIELDS = ["handles_personal_info", "hosting_location", "operator_agreement_status"]
DUPLICATE_DOMAIN = "Another vendor already uses this domain."


def _blank_values() -> dict[str, str]:
    values = {field: "" for field in FORM_FIELDS}
    values.update({field: "unknown" for field in ENUM_FIELDS})
    return values


def _validate(values: dict[str, str], db: Session, vendor_id: int | None = None):
    """Return (parsed form or None, errors by field)."""
    data = {key: val for key, val in values.items() if val.strip()}
    try:
        parsed = VendorForm(**data)
    except ValidationError as exc:
        return None, error_messages(exc)
    errors = validate_vendor_dates(parsed, clock.today())
    if parsed.primary_domain:
        query = select(Vendor.id).where(Vendor.primary_domain == parsed.primary_domain)
        if vendor_id is not None:
            query = query.where(Vendor.id != vendor_id)
        if db.scalar(query) is not None:
            errors["primary_domain"] = DUPLICATE_DOMAIN
    return (None, errors) if errors else (parsed, {})


def _render_form(
    request, *, title, action, values, errors, vendor_id=None, from_application=None, status_code=200
):
    return templates.TemplateResponse(
        request,
        "vendor_form.html",
        {
            "title": title,
            "action": action,
            "values": values,
            "errors": errors,
            "vendor_id": vendor_id,
            "from_application": from_application,
        },
        status_code=status_code,
    )


def _unassigned_application(db: Session, raw_id: str | None) -> Application | None:
    """The application a new vendor is being created for, if it is real and still unassigned."""
    if not raw_id or not raw_id.isdigit() or len(raw_id) > 9:
        return None
    application = db.get(Application, int(raw_id))
    return application if application is not None and application.vendor_id is None else None


def _get_vendor_or_404(db: Session, vendor_id: int) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.get("/vendors")
def list_vendors(
    request: Request, msg: str | None = None, level: str | None = None, db: Session = Depends(get_db)
):
    vendors = db.scalars(
        select(Vendor)
        .options(selectinload(Vendor.applications))
        .order_by(func.lower(Vendor.name))
    ).all()
    today = clock.today()
    scores = {v.id: score_vendor(facts_from_vendor(v), today) for v in vendors}
    if level in ("high", "medium", "low"):
        vendors = [v for v in vendors if scores[v.id].level == level]
    else:
        level = None  # anything else is ignored
    return templates.TemplateResponse(
        request,
        "vendors_list.html",
        {"vendors": vendors, "scores": scores, "level": level, "message": MESSAGES.get(msg or "")},
    )


@router.get("/vendors/new")
def new_vendor_form(request: Request, from_application: str = "", db: Session = Depends(get_db)):
    values = _blank_values()
    application = _unassigned_application(db, from_application)
    if application is not None:  # start from what the import already knows
        values["name"] = application.name
        values["primary_domain"] = application.source_domain or ""
    return _render_form(
        request, title="Add vendor", action="/vendors",
        values=values, errors={}, from_application=application,
    )


@router.get("/vendors/{vendor_id}")
def vendor_detail(
    vendor_id: int, request: Request, msg: str | None = None, db: Session = Depends(get_db)
):
    vendor = _get_vendor_or_404(db, vendor_id)
    applications = sorted(vendor.applications, key=lambda a: a.name.lower())
    today = clock.today()
    return templates.TemplateResponse(
        request,
        "vendor_detail.html",
        {
            "vendor": vendor,
            "applications": applications,
            "message": MESSAGES.get(msg or ""),
            "score": score_vendor(facts_from_vendor(vendor), today),
            "review": review_status(vendor.last_reviewed, vendor.next_review_due, today),
        },
    )


@router.post("/vendors")
async def create_vendor(request: Request, db: Session = Depends(get_db)):
    values = await read_form(request, FORM_FIELDS)
    form = await request.form()
    application = _unassigned_application(db, str(form.get("from_application") or ""))
    parsed, errors = _validate(values, db)
    if parsed is not None:
        vendor = Vendor(**parsed.model_dump())
        db.add(vendor)
        try:
            db.flush()  # gives the vendor an id before anything is linked to it
            if application is not None:
                application.vendor_id = vendor.id
                application.match_method = "manual"  # a person made this link
            db.commit()
        except IntegrityError:  # two people saving the same domain at once
            db.rollback()
            errors = {"primary_domain": DUPLICATE_DOMAIN}
        else:
            if application is not None:  # show the vendor with its newly linked application
                return RedirectResponse(f"/vendors/{vendor.id}?msg=created_linked", status_code=303)
            return RedirectResponse("/vendors?msg=created", status_code=303)
    return _render_form(
        request, title="Add vendor", action="/vendors",
        values=values, errors=errors, from_application=application, status_code=422,
    )


@router.get("/vendors/{vendor_id}/edit")
def edit_vendor_form(vendor_id: int, request: Request, db: Session = Depends(get_db)):
    vendor = _get_vendor_or_404(db, vendor_id)
    return _render_form(
        request, title=f"Edit {vendor.name}", action=f"/vendors/{vendor.id}/edit",
        values=values_from_object(vendor, FORM_FIELDS), errors={}, vendor_id=vendor.id,
    )


@router.post("/vendors/{vendor_id}/edit")
async def update_vendor(vendor_id: int, request: Request, db: Session = Depends(get_db)):
    vendor = _get_vendor_or_404(db, vendor_id)
    values = await read_form(request, FORM_FIELDS)
    parsed, errors = _validate(values, db, vendor_id=vendor.id)
    if parsed is not None:
        for field, value in parsed.model_dump().items():
            setattr(vendor, field, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            errors = {"primary_domain": DUPLICATE_DOMAIN}
        else:
            return RedirectResponse("/vendors?msg=updated", status_code=303)
    return _render_form(
        request, title=f"Edit {vendor.name}", action=f"/vendors/{vendor.id}/edit",
        values=values, errors=errors, vendor_id=vendor.id, status_code=422,
    )


@router.get("/vendors/{vendor_id}/delete")
def confirm_delete(vendor_id: int, request: Request, db: Session = Depends(get_db)):
    vendor = _get_vendor_or_404(db, vendor_id)
    return templates.TemplateResponse(
        request,
        "vendor_delete.html",
        {"vendor": vendor, "app_count": len(vendor.applications)},
    )


@router.post("/vendors/{vendor_id}/delete")
def delete_vendor(vendor_id: int, db: Session = Depends(get_db)):
    vendor = _get_vendor_or_404(db, vendor_id)
    db.delete(vendor)  # the database sets its applications' vendor_id to NULL
    db.commit()
    return RedirectResponse("/vendors?msg=deleted", status_code=303)
