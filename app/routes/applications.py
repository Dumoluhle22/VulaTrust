"""Application screens: list, add, edit, delete (issue 7)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.formutils import error_messages, read_form, values_from_object
from app.matching import VendorMatcher
from app.messages import MESSAGES
from app.models import Application, Vendor
from app.schemas import ApplicationForm
from app.templating import templates

router = APIRouter()

FORM_FIELDS = ["name", "vendor_id", "source", "user_count", "scopes", "privileged"]
BAD_VENDOR = "Choose a vendor from the list."


def _vendor_options(db: Session, include_none: bool = True) -> list[tuple[str, str]]:
    vendors = db.scalars(select(Vendor).order_by(func.lower(Vendor.name))).all()
    options = [("", "None (unassigned)")] if include_none else []
    for vendor in vendors:
        label = f"{vendor.name} ({vendor.primary_domain})" if vendor.primary_domain else vendor.name
        options.append((str(vendor.id), label))
    return options


def _validate(values: dict[str, str], db: Session):
    """Return (parsed form or None, errors by field)."""
    data = {key: val for key, val in values.items() if val.strip()}
    try:
        parsed = ApplicationForm(**data)
    except ValidationError as exc:
        return None, error_messages(exc)
    if parsed.vendor_id is not None and db.get(Vendor, parsed.vendor_id) is None:
        return None, {"vendor_id": BAD_VENDOR}
    return parsed, {}


def _after_save(vendor_id: int | None, key: str) -> RedirectResponse:
    """Go to the vendor's page if the application has one, otherwise the list."""
    target = f"/vendors/{vendor_id}" if vendor_id else "/applications"
    return RedirectResponse(f"{target}?msg={key}", status_code=303)


def _render_form(request, db, *, title, action, values, errors, status_code=200):
    return templates.TemplateResponse(
        request,
        "application_form.html",
        {
            "title": title,
            "action": action,
            "values": values,
            "errors": errors,
            "vendor_options": _vendor_options(db),
        },
        status_code=status_code,
    )


def _get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("/applications")
def list_applications(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    applications = db.scalars(
        select(Application)
        .options(selectinload(Application.vendor))
        .order_by(func.lower(Application.name))
    ).all()
    return templates.TemplateResponse(
        request,
        "applications_list.html",
        {"applications": applications, "message": MESSAGES.get(msg or "")},
    )


@router.get("/applications/unassigned")
def list_unassigned(request: Request, linked: str | None = None, db: Session = Depends(get_db)):
    applications = db.scalars(
        select(Application)
        .where(Application.vendor_id.is_(None))
        .order_by(func.lower(Application.name))
    ).all()
    linked_count = int(linked) if linked and linked.isdigit() and len(linked) <= 7 else None
    return templates.TemplateResponse(
        request,
        "unassigned_list.html",
        {
            "applications": applications,
            "linked_count": linked_count,
            "can_rematch": any(a.source_domain for a in applications),
        },
    )


@router.post("/applications/unassigned/rematch")
def rematch_unassigned(db: Session = Depends(get_db)):
    """Try again to match unassigned applications to vendors by domain."""
    vendors = db.execute(select(Vendor.id, Vendor.primary_domain)).all()
    matcher = VendorMatcher([(v.id, v.primary_domain) for v in vendors])
    linked = 0
    for application in db.scalars(
        select(Application).where(
            Application.vendor_id.is_(None), Application.source_domain.is_not(None)
        )
    ):
        match = matcher.match(application.source_domain)
        if match.vendor_id is not None:
            application.vendor_id = match.vendor_id
            application.match_method = match.method
            linked += 1
    db.commit()
    return RedirectResponse(f"/applications/unassigned?linked={linked}", status_code=303)


@router.get("/applications/new")
def new_application_form(request: Request, vendor_id: str = "", db: Session = Depends(get_db)):
    values = {
        "name": "", "vendor_id": vendor_id, "source": "manual",
        "user_count": "0", "scopes": "", "privileged": "unknown",
    }
    return _render_form(
        request, db, title="Add application", action="/applications",
        values=values, errors={},
    )


@router.post("/applications")
async def create_application(request: Request, db: Session = Depends(get_db)):
    values = await read_form(request, FORM_FIELDS)
    parsed, errors = _validate(values, db)
    if parsed is not None:
        data = parsed.model_dump()
        application = Application(
            **data, match_method="manual" if data["vendor_id"] else None
        )
        db.add(application)
        db.commit()
        return _after_save(application.vendor_id, "app_created")
    return _render_form(
        request, db, title="Add application", action="/applications",
        values=values, errors=errors, status_code=422,
    )


@router.get("/applications/{application_id}/edit")
def edit_application_form(application_id: int, request: Request, db: Session = Depends(get_db)):
    application = _get_application_or_404(db, application_id)
    return _render_form(
        request, db, title=f"Edit {application.name}",
        action=f"/applications/{application.id}/edit",
        values=values_from_object(application, FORM_FIELDS), errors={},
    )


@router.post("/applications/{application_id}/edit")
async def update_application(
    application_id: int, request: Request, db: Session = Depends(get_db)
):
    application = _get_application_or_404(db, application_id)
    values = await read_form(request, FORM_FIELDS)
    parsed, errors = _validate(values, db)
    if parsed is not None:
        old_vendor_id = application.vendor_id
        for field, value in parsed.model_dump().items():
            setattr(application, field, value)
        if application.vendor_id != old_vendor_id:
            # The link was changed by a person, so record that. A link that is
            # left alone keeps whatever match_method it already had.
            application.match_method = "manual" if application.vendor_id else None
        db.commit()
        return _after_save(application.vendor_id, "app_updated")
    return _render_form(
        request, db, title=f"Edit {application.name}",
        action=f"/applications/{application.id}/edit",
        values=values, errors=errors, status_code=422,
    )


@router.get("/applications/{application_id}/delete")
def confirm_delete(application_id: int, request: Request, db: Session = Depends(get_db)):
    application = _get_application_or_404(db, application_id)
    return templates.TemplateResponse(
        request, "application_delete.html", {"application": application}
    )


@router.post("/applications/{application_id}/delete")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    application = _get_application_or_404(db, application_id)
    vendor_id = application.vendor_id
    db.delete(application)
    db.commit()
    return _after_save(vendor_id, "app_deleted")


def _render_assign(request, db, application, *, error=None, status_code=200):
    return templates.TemplateResponse(
        request,
        "application_assign.html",
        {
            "application": application,
            "vendor_options": _vendor_options(db, include_none=False),
            "values": {"vendor_id": str(application.vendor_id or "")},
            "errors": {"vendor_id": error} if error else {},
        },
        status_code=status_code,
    )


@router.get("/applications/{application_id}/assign")
def assign_form(application_id: int, request: Request, db: Session = Depends(get_db)):
    application = _get_application_or_404(db, application_id)
    return _render_assign(request, db, application)


@router.post("/applications/{application_id}/assign")
async def assign_application(
    application_id: int, request: Request, db: Session = Depends(get_db)
):
    application = _get_application_or_404(db, application_id)
    form = await request.form()
    raw = str(form.get("vendor_id") or "")
    vendor = db.get(Vendor, int(raw)) if raw.isdigit() and len(raw) <= 9 else None
    if vendor is None:
        return _render_assign(request, db, application, error=BAD_VENDOR, status_code=422)
    application.vendor_id = vendor.id
    application.match_method = "manual"  # a person made this link
    db.commit()
    return RedirectResponse(f"/vendors/{vendor.id}?msg=app_linked", status_code=303)
