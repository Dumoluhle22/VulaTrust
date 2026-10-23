"""CSV import: check, preview, confirm, history (issues 9 and 11)."""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.csv_import import MAX_FILE_BYTES, MAX_ROWS, REQUIRED_COLUMNS, CsvCheckResult, check_csv
from app.database import get_db
from app.importer import ImportPlan, apply_import, build_plan
from app.messages import MESSAGES
from app.models import Application, ImportBatch
from app.pending_imports import pending_imports
from app.templating import templates

logger = logging.getLogger(__name__)
router = APIRouter()

PREVIEW_ROWS = 20
TEMPLATE_CSV = (
    ",".join(REQUIRED_COLUMNS) + "\r\n"
    "Example Scheduler,examplescheduler.example,google,12,calendar read/write,no\r\n"
)


def _render(
    request: Request,
    result: CsvCheckResult | None,
    *,
    filename: str = "",
    plan: ImportPlan | None = None,
    token: str | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request,
        "import.html",
        {
            "result": result,
            "filename": filename,
            "plan": plan,
            "token": token,
            "max_mb": MAX_FILE_BYTES // 1_048_576,
            "max_rows": MAX_ROWS,
            "columns": REQUIRED_COLUMNS,
            "preview": plan.rows[:PREVIEW_ROWS] if plan else [],
            "preview_rows": PREVIEW_ROWS,
        },
        status_code=status_code,
    )


@router.get("/import")
def import_page(request: Request):
    return _render(request, None)


@router.get("/import/template.csv")
def download_template():
    return Response(
        TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="vulatrust-import-template.csv"'},
    )


@router.post("/import")
async def check_upload(
    request: Request,
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    """Step 1: check the file and show what would happen. Saves nothing."""
    if file is None or not file.filename:
        result = CsvCheckResult(file_error="Choose a CSV file to check.")
        return _render(request, result, status_code=422)
    data = await file.read(MAX_FILE_BYTES + 1)  # never read more than the limit
    result = check_csv(data, file.filename)
    if result.file_error:
        return _render(request, result, filename=file.filename, status_code=422)
    plan = build_plan(db, result)
    token = pending_imports.put(file.filename, data) if plan.rows else None
    return _render(request, result, filename=file.filename, plan=plan, token=token)


@router.post("/import/confirm")
async def confirm_import(request: Request, db: Session = Depends(get_db)):
    """Step 2: save what the preview showed, as one all-or-nothing import."""
    form = await request.form()
    pending = pending_imports.take(str(form.get("token") or ""))
    if pending is None:
        result = CsvCheckResult(
            file_error="This preview has expired or was already used. Upload the file again."
        )
        return _render(request, result, status_code=422)

    filename, data = pending
    result = check_csv(data, filename)
    if result.file_error or not result.valid:
        failed = CsvCheckResult(file_error=result.file_error or "There is nothing to import.")
        return _render(request, failed, filename=filename, status_code=422)

    plan = build_plan(db, result)  # re-planned against the vendors as they are now
    try:
        batch = apply_import(db, filename, plan)
    except Exception:
        logger.exception("Import of %r failed", filename)
        failed = CsvCheckResult(file_error="The import failed, and nothing was saved. Please try again.")
        return _render(request, failed, filename=filename, status_code=500)
    return RedirectResponse(f"/import/batches/{batch.id}?msg=import_done", status_code=303)


@router.get("/import/history")
def import_history(request: Request, db: Session = Depends(get_db)):
    batches = db.scalars(select(ImportBatch).order_by(ImportBatch.id.desc())).all()
    return templates.TemplateResponse(request, "import_history.html", {"batches": batches})


@router.get("/import/batches/{batch_id}")
def import_batch(
    batch_id: int, request: Request, msg: str | None = None, db: Session = Depends(get_db)
):
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import not found")
    applications = db.scalars(
        select(Application)
        .options(selectinload(Application.vendor))
        .where(Application.import_batch_id == batch_id)
        .order_by(func.lower(Application.name))
    ).all()
    return templates.TemplateResponse(
        request,
        "import_batch.html",
        {"batch": batch, "applications": applications, "message": MESSAGES.get(msg or "")},
    )
