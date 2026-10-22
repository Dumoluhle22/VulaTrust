"""VulaTrust web application entry point."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.routes import applications, imports, vendors
from app.templating import templates


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create tables on first run.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="VulaTrust", lifespan=lifespan)
app.include_router(vendors.router)
app.include_router(applications.router)
app.include_router(imports.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    vendor_count = db.scalar(select(func.count(models.Vendor.id))) or 0
    application_count = db.scalar(select(func.count(models.Application.id))) or 0
    unassigned_count = (
        db.scalar(
            select(func.count(models.Application.id)).where(
                models.Application.vendor_id.is_(None)
            )
        )
        or 0
    )
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "vendor_count": vendor_count,
            "application_count": application_count,
            "unassigned_count": unassigned_count,
        },
    )
