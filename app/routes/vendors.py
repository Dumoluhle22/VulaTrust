"""Vendor screens: list, add, edit, delete (issue 6)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.formutils import error_messages, read_form, values_from_object
from app.messages import MESSAGES
from app.models import Vendor
from app.schemas import VendorForm
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
    if parsed.primary_domain:
        query = select(Vendor.id).where(Vendor.primary_domain == parsed.primary_domain)
        if vendor_id is not None:
            query = query.where(Vendor.id != vendor_id)
        if db.scalar(query) is not None:
            return None, {"primary_domain": DUPLICATE_DOMAIN}
    return parsed, {}


def _render_form(request, *, title, action, values, errors, vendor_id=None, status_code=200):
    return templates.TemplateResponse(
        request,
        "vendor_form.html",
        {
            "title": title,
            "action": action,
            "values": values,
            "errors": errors,
            "vendor_id": vendor_id,
        },
        status_code=status_code,
    )


def _get_vendor_or_404(db: Session, vendor_id: int) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.get("/vendors")
def list_vendors(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    vendors = db.scalars(
        select(Vendor)
        .options(selectinload(Vendor.applications))
        .order_by(func.lower(Vendor.name))
    ).all()
    return templates.TemplateResponse(
        request,
        "vendors_list.html",
        {"vendors": vendors, "message": MESSAGES.get(msg or "")},
    )


@router.get("/vendors/new")
def new_vendor_form(request: Request):
    return _render_form(
        request, title="Add vendor", action="/vendors",
        values=_blank_values(), errors={},
    )


@router.get("/vendors/{vendor_id}")
def vendor_detail(
    vendor_id: int, request: Request, msg: str | None = None, db: Session = Depends(get_db)
):
    vendor = _get_vendor_or_404(db, vendor_id)
    applications = sorted(vendor.applications, key=lambda a: a.name.lower())
    return templates.TemplateResponse(
        request,
        "vendor_detail.html",
        {"vendor": vendor, "applications": applications, "message": MESSAGES.get(msg or "")},
    )


@router.post("/vendors")
async def create_vendor(request: Request, db: Session = Depends(get_db)):
    values = await read_form(request, FORM_FIELDS)
    parsed, errors = _validate(values, db)
    if parsed is not None:
        db.add(Vendor(**parsed.model_dump()))
        try:
            db.commit()
        except IntegrityError:  # two people saving the same domain at once
            db.rollback()
            errors = {"primary_domain": DUPLICATE_DOMAIN}
        else:
            return RedirectResponse("/vendors?msg=created", status_code=303)
    return _render_form(
        request, title="Add vendor", action="/vendors",
        values=values, errors=errors, status_code=422,
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
