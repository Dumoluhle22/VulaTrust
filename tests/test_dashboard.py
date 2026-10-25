from datetime import date
from pathlib import Path

import pytest

from app.csv_import import check_csv
from app.dashboard import build_dashboard
from app.importer import apply_import, build_plan
from app.models import AgreementStatus, Application, TriState, Vendor
from app.seed import load_vendors

TODAY = date(2026, 10, 13)
SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "apps.csv"


@pytest.fixture
def sample(db):
    """The eight sample vendors with the sample import applied."""
    load_vendors(db)
    apply_import(db, "apps.csv", build_plan(db, check_csv(SAMPLE.read_bytes(), "apps.csv")))
    return db


def names(rows):
    return [row.vendor.name for row in rows]


# ---- the numbers match sample_data/README.md ---------------------------------------

def test_counts_and_levels(sample):
    d = build_dashboard(sample, TODAY)
    assert (d.vendor_count, d.application_count, d.unassigned_count) == (8, 16, 5)
    assert d.level_counts == {"high": 1, "medium": 4, "low": 3}


def test_highest_scores_come_first(sample):
    top = build_dashboard(sample, TODAY).top
    assert names(top) == ["ClinicNotes", "ChatBridge", "MailBlast", "LedgerLite", "Brightlearn LMS"]
    assert [row.score.score for row in top] == [85, 68, 60, 50, 40]


def test_vendors_without_a_signed_agreement_that_handle_personal_info(sample):
    d = build_dashboard(sample, TODAY)
    assert names(d.no_agreement) == ["ClinicNotes", "ChatBridge", "MailBlast", "Brightlearn LMS"]


def test_overdue_and_never_reviewed(sample):
    d = build_dashboard(sample, TODAY)
    # never reviewed first, then the longest overdue
    assert names(d.overdue) == ["ChatBridge", "LedgerLite", "MailBlast", "ClinicNotes"]


def test_vendors_with_no_owner(sample):
    assert names(build_dashboard(sample, TODAY).no_owner) == ["ChatBridge", "LedgerLite"]


def test_least_complete_records_first(sample):
    d = build_dashboard(sample, TODAY)
    assert names(d.incomplete) == ["ChatBridge", "LedgerLite"]
    assert [row.score.completeness.known for row in d.incomplete] == [0, 6]


# ---- edge cases -----------------------------------------------------------------------

def test_a_vendor_that_certainly_handles_no_personal_info_is_left_out(db):
    db.add(Vendor(name="Design", handles_personal_info=TriState.NO))
    db.add(Vendor(name="Maybe", handles_personal_info=TriState.UNKNOWN))
    db.commit()
    assert names(build_dashboard(db, TODAY).no_agreement) == ["Maybe"]


def test_a_signed_agreement_removes_a_vendor_from_the_list(db):
    db.add(Vendor(
        name="Signed", handles_personal_info=TriState.YES,
        operator_agreement_status=AgreementStatus.SIGNED, operator_agreement_date=date(2026, 1, 1),
    ))
    db.commit()
    assert build_dashboard(db, TODAY).no_agreement == []


def test_the_incomplete_list_is_capped_at_ten(db):
    db.add_all([Vendor(name=f"V{i:02d}") for i in range(15)])
    db.commit()
    assert len(build_dashboard(db, TODAY).incomplete) == 10


def test_ties_are_broken_by_name(db):
    db.add_all([Vendor(name="b"), Vendor(name="A"), Vendor(name="c")])
    db.commit()
    assert names(build_dashboard(db, TODAY).top) == ["A", "b", "c"]


# ---- the page ------------------------------------------------------------------------------

def test_dashboard_page_shows_the_counts(client, sample):
    html = client.get("/").text
    assert "<strong>8</strong>Vendors" in html
    assert "<strong>16</strong>Applications" in html
    assert '<a class="card" href="/applications/unassigned"><strong>5</strong>Unassigned applications</a>' in html
    assert '<a class="card" href="/vendors?level=high"><strong>1</strong>High risk</a>' in html
    assert '<a class="card" href="/vendors?level=medium"><strong>4</strong>Medium risk</a>' in html
    assert '<a class="card" href="/vendors?level=low"><strong>3</strong>Low risk</a>' in html


def test_dashboard_lists_link_to_vendor_pages(client, sample):
    html = client.get("/").text
    clinic = sample.query(Vendor).filter_by(name="ClinicNotes").one()
    assert f'<a href="/vendors/{clinic.id}">ClinicNotes</a>' in html
    assert "No signed operator agreement (4)" in html
    assert "Reviews overdue or never done (4)" in html
    assert "Vendors with no owner (2)" in html
    assert "Least complete records (2)" in html
    assert "5 applications have no vendor" in html


def test_dashboard_shows_unknown_never_blank(client, sample):
    html = client.get("/").text
    section = html.split("No signed operator agreement")[1].split("Reviews overdue")[0]
    assert "<td>Unknown</td>" in section          # ChatBridge: personal info and agreement unknown
    assert "<td></td>" not in section
    least = html.split("Least complete records")[1]
    assert "0 of 7" in least and "6 of 7" in least
    assert "Handles personal information, Hosting location" in least


def test_dashboard_shows_review_status_labels(client, sample):
    section = client.get("/").text.split("Reviews overdue or never done")[1].split("Vendors with no owner")[0]
    assert "Never reviewed" in section
    assert "Overdue" in section


def test_empty_database_shows_a_welcome_and_empty_states(client):
    html = client.get("/").text
    assert "Nothing here yet." in html
    assert 'href="/vendors/new"' in html and 'href="/import"' in html
    assert "<strong>0</strong>Vendors" in html
    assert "No vendors yet, so there are no scores to show." in html
    assert "Every vendor that handles or may handle personal information has a signed agreement recorded." in html
    assert "No reviews are overdue." in html
    assert "Every vendor has an owner." in html
    assert "Every vendor record is complete." in html
    assert "Every application is linked to a vendor." in html


def test_empty_states_when_everything_is_in_order(client, db):
    vendor = Vendor(
        name="Perfect", owner="T", handles_personal_info=TriState.NO,
        hosting_location="south_africa", operator_agreement_status=AgreementStatus.NONE,
        last_reviewed=date(2026, 9, 1), next_review_due=date(2027, 9, 1),
    )
    vendor.applications.append(Application(name="App", privileged=TriState.NO, user_count=1))
    db.add(vendor)
    db.commit()
    html = client.get("/").text
    assert "Nothing here yet." not in html
    assert "No reviews are overdue." in html
    assert "Every vendor has an owner." in html
    assert "Every vendor record is complete." in html
    assert "Every application is linked to a vendor." in html


def test_dashboard_escapes_vendor_names(client, db):
    db.add(Vendor(name="<script>alert(1)</script>"))
    db.commit()
    html = client.get("/").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_dashboard_alias_redirects_home(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/"


# ---- the level filter on the vendor list --------------------------------------------------

def test_vendor_list_can_be_filtered_by_level(client, sample):
    high = client.get("/vendors?level=high").text
    assert "ClinicNotes" in high and "PayTrack" not in high
    assert "Showing <strong>high</strong> vendors only." in high
    low = client.get("/vendors?level=low").text
    assert all(n in low for n in ("PayTrack", "QuickSign", "DesignHub"))
    assert "ClinicNotes" not in low


def test_an_invalid_level_is_ignored(client, sample):
    for bad in ["critical", "' OR 1=1 --", "<script>", ""]:
        html = client.get("/vendors", params={"level": bad}).text
        assert "Showing <strong>" not in html
        assert "ClinicNotes" in html and "PayTrack" in html


def test_an_empty_level_filter_explains_itself(client, db):
    db.add(Vendor(name="Only"))
    db.commit()
    assert "No vendors are at this level." in client.get("/vendors?level=low").text
