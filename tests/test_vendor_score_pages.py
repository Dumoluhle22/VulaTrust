from datetime import date

from app.models import (
    AgreementStatus, Application, HostingLocation, TriState, Vendor,
)


def make_vendor(db, **fields):
    vendor = Vendor(name=fields.pop("name", "PayTrack"), **fields)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def high_risk(db):
    vendor = make_vendor(
        db, name="ClinicNotes", handles_personal_info=TriState.YES,
        hosting_location=HostingLocation.OUTSIDE_SOUTH_AFRICA,
        operator_agreement_status=AgreementStatus.NONE, owner="Sipho",
        last_reviewed=date(2026, 1, 15), next_review_due=date(2026, 7, 15),
    )
    vendor.applications.append(Application(name="Web", user_count=9, privileged=TriState.YES))
    db.commit()
    return vendor


# ---- vendor page ------------------------------------------------------------------------

def test_vendor_page_shows_score_level_and_factors(client, db):
    vendor = high_risk(db)
    html = client.get(f"/vendors/{vendor.id}").text
    assert "85 / 100: High" in html
    assert '<span class="level level-high">' in html
    for label in [
        "Personal information without a signed operator agreement",
        "Broad (privileged) access",
        "Review overdue or never done",
        "Hosted outside South Africa",
        "Many users connected",
    ]:
        assert label in html
    assert "35 of 35" in html and "20 of 20" in html
    assert "The review was due on 2026-07-15." in html
    assert "No owner assigned" in html.split("Checked and not adding points:")[1]  # an owner exists


def test_unknown_inputs_are_labelled_unverified_with_completeness(client, db):
    vendor = make_vendor(db, name="Mystery")
    html = client.get(f"/vendors/{vendor.id}").text
    assert "63 / 100: Medium" in html
    assert '<span class="tag">unverified</span>' in html
    assert '<span class="tag">confirmed</span>' in html   # no owner and never reviewed are certain
    assert "0 of 7 fields known." in html
    assert "Missing: Handles personal information, Hosting location" in html
    assert "17.5 of 35" in html
    assert "No applications are recorded, so privileged access is unverified." in html


def test_clean_vendor_has_no_factors(client, db):
    vendor = make_vendor(
        db, handles_personal_info=TriState.NO, hosting_location=HostingLocation.SOUTH_AFRICA,
        operator_agreement_status=AgreementStatus.NONE, owner="Thandi",
        last_reviewed=date(2026, 9, 1), next_review_due=date(2027, 9, 1),
    )
    vendor.applications.append(Application(name="App", user_count=1, privileged=TriState.NO))
    db.commit()
    html = client.get(f"/vendors/{vendor.id}").text
    assert "0 / 100: Low" in html
    assert "No risk factors apply to this vendor." in html
    assert "7 of 7 fields known." in html
    assert "Missing:" not in html


def test_vendor_page_carries_the_required_notes(client, db):
    vendor = make_vendor(db)
    html = client.get(f"/vendors/{vendor.id}").text
    assert "not proof that a vendor is secure or insecure" in html
    assert "add half their points because the information is missing" in html
    assert "Recording an agreement does not mean it is legally adequate." in html


def test_vendor_page_shows_the_review_status(client, db):
    cases = {
        "Never reviewed": dict(),
        "Overdue": dict(last_reviewed=date(2026, 1, 1), next_review_due=date(2026, 10, 12)),
        "Scheduled": dict(last_reviewed=date(2026, 1, 1), next_review_due=date(2026, 10, 13)),
        "Reviewed, but no next review date": dict(last_reviewed=date(2026, 1, 1)),
    }
    for index, (label, fields) in enumerate(cases.items()):
        vendor = make_vendor(db, name=f"V{index}", **fields)
        html = client.get(f"/vendors/{vendor.id}").text
        assert f"<th>Review status</th><td>{label}</td>" in html, label


def test_signed_date_is_shown_on_the_vendor_page(client, db):
    vendor = make_vendor(
        db, operator_agreement_status=AgreementStatus.SIGNED, operator_agreement_date=date(2026, 3, 10)
    )
    assert "Signed (signed 2026-03-10)" in client.get(f"/vendors/{vendor.id}").text


def test_explanations_are_escaped(client, db):
    vendor = make_vendor(db, name="<script>alert(1)</script>", owner="<b>x</b>")
    html = client.get(f"/vendors/{vendor.id}").text
    assert "<script>alert(1)</script>" not in html


# ---- vendor list --------------------------------------------------------------------------------

def test_list_shows_each_vendors_score_and_level(client, db):
    high_risk(db)
    make_vendor(
        db, name="Clean", handles_personal_info=TriState.NO, hosting_location=HostingLocation.SOUTH_AFRICA,
        owner="T", last_reviewed=date(2026, 9, 1), next_review_due=date(2027, 9, 1),
    )
    html = client.get("/vendors").text
    assert '<span class="level level-high">85 High</span>' in html
    assert "<th>Score</th>" in html
    assert "Low</span>" in html


# ---- scores follow the data ----------------------------------------------------------------------

def test_score_changes_when_a_vendor_is_edited_through_the_form(client, db):
    client.post("/vendors", data={
        "name": "PayTrack", "owner": "Thandi", "handles_personal_info": "yes",
        "hosting_location": "south_africa", "operator_agreement_status": "none",
        "last_reviewed": "2026-09-01", "next_review_due": "2027-09-01",
    })
    vendor = db.query(Vendor).one()
    # personal info 35 and no applications (privileged unverified 10)
    assert "45 / 100: Medium" in client.get(f"/vendors/{vendor.id}").text

    client.post(f"/vendors/{vendor.id}/edit", data={
        "name": "PayTrack", "owner": "Thandi", "handles_personal_info": "yes",
        "hosting_location": "south_africa", "operator_agreement_status": "signed",
        "operator_agreement_date": "2026-10-01",
        "last_reviewed": "2026-09-01", "next_review_due": "2027-09-01",
    })
    assert "10 / 100: Low" in client.get(f"/vendors/{vendor.id}").text


def test_score_changes_when_an_application_is_added(client, db):
    vendor = make_vendor(
        db, handles_personal_info=TriState.NO, hosting_location=HostingLocation.SOUTH_AFRICA,
        owner="T", last_reviewed=date(2026, 9, 1), next_review_due=date(2027, 9, 1),
    )
    assert "10 / 100: Low" in client.get(f"/vendors/{vendor.id}").text   # no apps: privileged unverified
    client.post("/applications", data={
        "name": "Mail", "vendor_id": str(vendor.id), "privileged": "yes", "user_count": "2",
    })
    assert "20 / 100: Low" in client.get(f"/vendors/{vendor.id}").text
