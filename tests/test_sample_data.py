import csv
from pathlib import Path

from app.models import AgreementStatus, HostingLocation, TriState, Vendor
from app.seed import DEFAULT_PATH, load_vendors

APPS_CSV = Path(DEFAULT_PATH).parent / "apps.csv"


def test_vendors_csv_loads_and_is_repeatable(db):
    assert load_vendors(db) == 8
    assert load_vendors(db) == 0  # running again adds nothing
    assert db.query(Vendor).count() == 8


def test_vendor_edge_cases_are_present(db):
    load_vendors(db)
    chatbridge = db.query(Vendor).filter_by(name="ChatBridge").one()
    assert chatbridge.owner is None
    assert chatbridge.handles_personal_info == TriState.UNKNOWN
    assert chatbridge.hosting_location == HostingLocation.UNKNOWN
    assert chatbridge.operator_agreement_status == AgreementStatus.UNKNOWN
    assert chatbridge.last_reviewed is None

    ledger = db.query(Vendor).filter_by(name="LedgerLite").one()
    assert ledger.owner is None
    assert ledger.operator_agreement_status == AgreementStatus.SIGNED


def test_apps_csv_shape():
    with open(APPS_CSV, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == [
        "app_name", "vendor_domain", "source", "user_count", "scopes", "privileged",
    ]
    assert len(rows) == 23
    assert sum(1 for r in rows if len(r["scopes"]) > 500) == 1
