"""VulaTrust web application entry point (issue 1)."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create tables on first run (issue 5: "database created automatically").
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="VulaTrust", lifespan=lifespan)


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
