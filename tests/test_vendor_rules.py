from datetime import date

import pytest

from app.models import AgreementStatus, Vendor
from app.schemas import VendorForm, validate_vendor_dates

TODAY = date(2026, 10, 13)   # the fixed date every test runs on


def post_vendor(client, **fields):
    data = {"name": "PayTrack"}
    data.update(fields)
    return client.post("/vendors", data=data, follow_redirects=False)


# ---- unit tests of the rules ---------------------------------------------------------

def form(**fields):
    return VendorForm(name="V", **fields)


def test_unsigned_vendors_need_no_dates():
    assert validate_vendor_dates(form(), TODAY) == {}


def test_signed_requires_a_date():
    errors = validate_vendor_dates(form(operator_agreement_status="signed"), TODAY)
    assert errors == {"operator_agreement_date": "Enter the date the agreement was signed."}


@pytest.mark.parametrize("status", ["none", "requested", "unknown"])
def test_a_date_is_only_allowed_when_signed(status):
    errors = validate_vendor_dates(form(operator_agreement_status=status, operator_agreement_date="2026-01-01"), TODAY)
    assert "Only enter a date when the agreement is signed" in errors["operator_agreement_date"]


def test_signing_date_boundaries():
    ok = lambda d: validate_vendor_dates(form(operator_agreement_status="signed", operator_agreement_date=d), TODAY)
    assert ok("2026-10-13") == {}     # today is fine
    assert ok("2020-01-01") == {}
    assert ok("2026-10-14") == {"operator_agreement_date": "The signing date cannot be in the future."}


def test_last_reviewed_cannot_be_in_the_future():
    assert validate_vendor_dates(form(last_reviewed="2026-10-13"), TODAY) == {}
    assert "last_reviewed" in validate_vendor_dates(form(last_reviewed="2026-10-14"), TODAY)


def test_next_review_cannot_be_before_the_last_review():
    ok = lambda last, nxt: validate_vendor_dates(form(last_reviewed=last, next_review_due=nxt), TODAY)
    assert ok("2026-06-01", "2026-06-01") == {}      # the same day is fine
    assert ok("2026-06-01", "2027-06-01") == {}
    assert ok("2026-06-01", "2026-05-31") == {"next_review_due": "Next review due cannot be before the last review."}
    assert ok(None, "2020-01-01") == {}              # nothing to compare against


# ---- through the form ----------------------------------------------------------------------

def test_signed_without_a_date_is_rejected_by_the_form(client, db):
    response = post_vendor(client, operator_agreement_status="signed")
    assert response.status_code == 422
    assert "Enter the date the agreement was signed." in response.text
    assert db.query(Vendor).count() == 0


def test_signed_with_a_valid_date_is_saved(client, db):
    response = post_vendor(client, operator_agreement_status="signed", operator_agreement_date="2026-10-13")
    assert response.status_code == 303
    vendor = db.query(Vendor).one()
    assert vendor.operator_agreement_status == AgreementStatus.SIGNED
    assert vendor.operator_agreement_date == date(2026, 10, 13)


def test_future_signing_date_is_rejected_by_the_form(client, db):
    response = post_vendor(client, operator_agreement_status="signed", operator_agreement_date="2026-10-14")
    assert response.status_code == 422
    assert "The signing date cannot be in the future." in response.text
    assert db.query(Vendor).count() == 0


def test_a_date_with_an_unsigned_status_is_rejected_by_the_form(client):
    response = post_vendor(client, operator_agreement_status="requested", operator_agreement_date="2026-01-01")
    assert response.status_code == 422
    assert "Only enter a date when the agreement is signed" in response.text


def test_review_date_rules_through_the_form(client, db):
    future = post_vendor(client, last_reviewed="2026-10-14")
    assert future.status_code == 422 and "Last reviewed cannot be in the future." in future.text
    backwards = post_vendor(client, last_reviewed="2026-06-01", next_review_due="2026-05-01")
    assert backwards.status_code == 422 and "cannot be before the last review" in backwards.text
    assert db.query(Vendor).count() == 0


def test_several_errors_are_shown_together(client):
    response = post_vendor(client, name="", operator_agreement_status="signed", last_reviewed="2030-01-01")
    assert response.status_code == 422
    # a required-field error stops the cross-field checks, so fix the name first
    assert "This field is required." in response.text


def test_changing_a_signed_vendor_to_requested_needs_the_old_date_cleared(client, db):
    post_vendor(client, operator_agreement_status="signed", operator_agreement_date="2026-03-10")
    vendor = db.query(Vendor).one()
    response = client.post(
        f"/vendors/{vendor.id}/edit",
        data={"name": "PayTrack", "operator_agreement_status": "requested", "operator_agreement_date": "2026-03-10"},
    )
    assert response.status_code == 422
    fixed = client.post(
        f"/vendors/{vendor.id}/edit",
        data={"name": "PayTrack", "operator_agreement_status": "requested"},
        follow_redirects=False,
    )
    assert fixed.status_code == 303
    db.expire_all()
    assert db.get(Vendor, vendor.id).operator_agreement_date is None


def test_the_form_explains_the_date_rules(client):
    html = client.get("/vendors/new").text
    assert "Required when the status is Signed" in html
    assert "Leave blank if this vendor has never been reviewed" in html
