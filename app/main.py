"""VulaTrust web application entry point."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import clock, models  # noqa: F401  (models registers the tables)
from app.dashboard import build_dashboard
from app.database import Base, engine, get_db
from app.routes import applications, imports, vendors
from app.security import CsrfError, csrf_error_page, require_csrf, security_middleware
from app.templating import templates


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create tables on first run.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="VulaTrust",
    lifespan=lifespan,
    # The generated API documentation pages are not needed and would list every route.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    dependencies=[Depends(require_csrf)],
)
app.middleware("http")(security_middleware)
app.add_exception_handler(CsrfError, csrf_error_page)
app.include_router(vendors.router)
app.include_router(applications.router)
app.include_router(imports.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "home.html", {"d": build_dashboard(db, clock.today())}
    )


@app.get("/dashboard")
def dashboard_alias():
    return RedirectResponse("/", status_code=303)
