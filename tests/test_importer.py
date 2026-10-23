from pathlib import Path

import pytest

import app.importer as importer
from app.csv_import import check_csv
from app.database import SessionLocal
from app.importer import apply_import, build_plan
from app.models import Application, ApplicationSource, ImportBatch, TriState, Vendor
from app.seed import load_vendors

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "apps.csv"
HEADER = "app_name,vendor_domain,source,user_count,scopes,privileged\n"


def run_import(db, text: str | bytes | None = None, filename: str = "apps.csv"):
    data = SAMPLE.read_bytes() if text is None else (text.encode() if isinstance(text, str) else text)
    plan = build_plan(db, check_csv(data, filename))
    return plan, apply_import(db, filename, plan)


@pytest.fixture
def seeded(db):
    load_vendors(db)
    return db


def apps_of(db, vendor_name):
    vendor = db.query(Vendor).filter_by(name=vendor_name).one()
    return sorted(a.name for a in vendor.applications)


# ---- the sample file gives the documented results ---------------------------

def test_plan_counts_match_the_sample_readme(seeded):
    plan = build_plan(seeded, check_csv(SAMPLE.read_bytes(), "apps.csv"))
    assert len(plan.rows) == 16
    assert plan.matched == 11
    assert plan.unassigned == 5
    assert plan.to_create == 16
    assert plan.to_update == 0
    assert seeded.query(Application).count() == 0  # planning saves nothing


def test_sample_import_batch_record(seeded):
    _plan, batch = run_import(seeded)
    assert batch.filename == "apps.csv"
    assert batch.source == ApplicationSource.CSV
    assert (batch.row_count, batch.created_count, batch.updated_count) == (23, 16, 0)
    assert (batch.matched_count, batch.unassigned_count) == (11, 5)
    assert (batch.rejected_count, batch.duplicate_count) == (6, 1)
    assert batch.imported_at is not None


def test_sample_import_links_applications_to_the_right_vendors(seeded):
    run_import(seeded)
    assert seeded.query(Application).count() == 16
    assert apps_of(seeded, "PayTrack") == ["PayTrack Mobile", "PayTrack Payroll"]
    assert apps_of(seeded, "ClinicNotes") == ["ClinicNotes Reports", "ClinicNotes Web"]
    assert apps_of(seeded, "DesignHub") == ["DesignHub", "DesignHub Plugin"]
    assert apps_of(seeded, "QuickSign") == ["QuickSign"]
    assert apps_of(seeded, "ChatBridge") == ["ChatBridge Desktop"]
    assert apps_of(seeded, "Brightlearn LMS") == ["Brightlearn LMS"]
    assert apps_of(seeded, "MailBlast") == ["MailBlast"]
    assert apps_of(seeded, "LedgerLite") == ["LedgerLite"]


def test_sample_import_records_how_each_match_was_made(seeded):
    run_import(seeded)
    by_name = {a.name: a for a in seeded.query(Application)}
    assert by_name["ClinicNotes Reports"].match_method == "subdomain"
    assert by_name["PayTrack Mobile"].match_method == "exact_domain"  # was PayTrack.example
    assert by_name["QuickSign"].match_method == "exact_domain"  # was a full URL
    assert by_name["Quick Notes"].match_method is None


def test_sample_import_leaves_five_unassigned_and_keeps_their_domains(seeded):
    run_import(seeded)
    unassigned = {a.name: a for a in seeded.query(Application).filter(Application.vendor_id.is_(None))}
    assert sorted(unassigned) == [
        "'=1+1 Report Tool", "Calendar Sync Pro", "Mystery PDF Tool", "Quick Notes", "Survey Maker",
    ]
    assert unassigned["Quick Notes"].source_domain == "quicknotes.example"
    assert unassigned["Mystery PDF Tool"].source_domain is None


def test_imported_values_are_stored(seeded):
    run_import(seeded)
    chat = seeded.query(Application).filter_by(name="ChatBridge Desktop").one()
    assert chat.source == ApplicationSource.GOOGLE
    assert chat.user_count == 12
    assert chat.privileged == TriState.UNKNOWN
    assert chat.import_batch is not None


def test_without_any_vendors_everything_is_unassigned(db):
    plan, batch = run_import(db)
    assert (plan.matched, plan.unassigned) == (0, 16)
    assert db.query(Application).filter(Application.vendor_id.is_(None)).count() == 16


# ---- re-importing ------------------------------------------------------------

def test_reimporting_the_same_file_updates_and_creates_no_copies(seeded):
    run_import(seeded)
    plan, second = run_import(seeded)
    assert plan.to_update == 16 and plan.to_create == 0
    assert (second.created_count, second.updated_count) == (0, 16)
    assert seeded.query(Application).count() == 16
    assert seeded.query(ImportBatch).count() == 2
    assert {a.import_batch_id for a in seeded.query(Application)} == {second.id}


def test_reimport_refreshes_values_from_the_file(seeded):
    run_import(seeded, HEADER + "Payroll,paytrack.example,google,3,old access,no\n")
    run_import(seeded, HEADER + "Payroll,paytrack.example,google,9,new access,yes\n")
    app_row = seeded.query(Application).one()
    assert (app_row.user_count, app_row.scopes, app_row.privileged) == (9, "new access", TriState.YES)


def test_a_new_vendor_picks_up_a_previously_unassigned_application(db):
    text = HEADER + "Notes,quicknotes.example,google,2,x,no\n"
    run_import(db, text)
    assert db.query(Application).one().vendor_id is None

    vendor = Vendor(name="QuickNotes", primary_domain="quicknotes.example")
    db.add(vendor)
    db.commit()
    run_import(db, text)

    app_row = db.query(Application).one()
    assert app_row.vendor_id == vendor.id
    assert app_row.match_method == "exact_domain"


def test_a_link_made_by_hand_survives_a_reimport(seeded):
    text = HEADER + "Mystery,quicknotes.example,google,2,x,no\n"
    run_import(seeded, text)
    app_row = seeded.query(Application).one()
    vendor = seeded.query(Vendor).filter_by(name="PayTrack").one()
    app_row.vendor_id, app_row.match_method = vendor.id, "manual"
    seeded.commit()

    plan, _batch = run_import(seeded, text)
    assert plan.rows[0].match.method == "manual"
    seeded.expire_all()
    app_row = seeded.query(Application).one()
    assert app_row.vendor_id == vendor.id
    assert app_row.match_method == "manual"


def test_applications_with_different_domains_are_not_merged(db):
    run_import(db, HEADER + "Sync,one.example,google,1,x,no\nSync,two.example,google,1,x,no\n")
    assert db.query(Application).count() == 2


def test_same_name_from_a_different_source_is_a_different_application(db):
    run_import(db, HEADER + "Sync,one.example,google,1,x,no\nSync,one.example,microsoft,1,x,no\n")
    assert db.query(Application).count() == 2


def test_hand_entered_applications_are_never_updated_by_an_import(seeded):
    seeded.add(Application(name="Payroll", source=ApplicationSource.CSV, user_count=1))
    seeded.commit()
    run_import(seeded, HEADER + "Payroll,,csv,50,x,yes\n")
    assert seeded.query(Application).count() == 2
    hand = seeded.query(Application).filter(Application.import_batch_id.is_(None)).one()
    assert hand.user_count == 1


# ---- all or nothing ------------------------------------------------------------

def test_a_failed_import_saves_nothing(seeded, monkeypatch):
    calls = {"n": 0}
    real = importer._write_row

    def flaky(db, batch, item):
        calls["n"] += 1
        if calls["n"] == 6:
            raise RuntimeError("disk full")
        return real(db, batch, item)

    monkeypatch.setattr(importer, "_write_row", flaky)
    plan = build_plan(seeded, check_csv(SAMPLE.read_bytes(), "apps.csv"))
    with pytest.raises(RuntimeError):
        apply_import(seeded, "apps.csv", plan)

    assert calls["n"] == 6
    with SessionLocal() as fresh:  # a brand-new session sees what was really saved
        assert fresh.query(Application).count() == 0
        assert fresh.query(ImportBatch).count() == 0
        assert fresh.query(Vendor).count() == 8  # earlier data untouched
