"""CSV check page (issue 9). Nothing is saved here yet; importing is issue 11."""
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import Response

from app.csv_import import MAX_FILE_BYTES, MAX_ROWS, REQUIRED_COLUMNS, CsvCheckResult, check_csv
from app.templating import templates

router = APIRouter()

PREVIEW_ROWS = 20
TEMPLATE_CSV = (
    ",".join(REQUIRED_COLUMNS) + "\r\n"
    "Example Scheduler,examplescheduler.example,google,12,calendar read/write,no\r\n"
)


def _render(request: Request, result: CsvCheckResult | None, filename: str = "", status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "import.html",
        {
            "result": result,
            "filename": filename,
            "max_mb": MAX_FILE_BYTES // 1_048_576,
            "max_rows": MAX_ROWS,
            "columns": REQUIRED_COLUMNS,
            "preview": result.valid[:PREVIEW_ROWS] if result else [],
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
async def check_upload(request: Request, file: UploadFile | None = File(default=None)):
    if file is None or not file.filename:
        result = CsvCheckResult(file_error="Choose a CSV file to check.")
        return _render(request, result, status_code=422)
    data = await file.read(MAX_FILE_BYTES + 1)  # never read more than the limit
    result = check_csv(data, file.filename)
    return _render(
        request, result, filename=file.filename,
        status_code=422 if result.file_error else 200,
    )
