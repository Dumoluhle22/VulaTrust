from datetime import date

from app.models import (
    AgreementStatus, Application, HostingLocation, TriState, Vendor,
)


def post_vendor(client, **fields):
    data = {"name": "PayTrack"}
    data.update(fields)
    return client.post("/vendors", data=data, follow_redirects=False)


# ---- list -----------------------------------------------------------------

def test_empty_list_shows_helpful_message(client):
    response = client.get("/vendors")
    assert response.status_code == 200
    assert "No vendors yet" in response.text


def test_list_shows_vendors_sorted_and_app_counts(client, db):
    zed = Vendor(name="zed corp", primary_domain="zed.example")
    alpha = Vendor(name="Alpha Ltd")
    alpha.applications.extend([Application(name="A1"), Application(name="A2")])
    db.add_all([zed, alpha])
    db.commit()

    html = client.get("/vendors").text
    assert html.index("Alpha Ltd") < html.index("zed corp")
    assert "zed.example" in html
    assert "<td>2</td>" in html  # Alpha has two applications


def test_unknown_values_are_shown_as_unknown_not_blank(client, db):
    db.add(Vendor(name="Mystery"))
    db.commit()
    html = client.get("/vendors").text
    assert html.count("Unknown") >= 3  # personal info, hosting, agreement
    assert "no owner" in html


def test_list_escapes_user_text(client, db):
    db.add(Vendor(name="<script>alert(1)</script>"))
    db.commit()
    html = client.get("/vendors").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# ---- create ---------------------------------------------------------------

def test_new_form_loads_with_unknown_defaults(client):
    response = client.get("/vendors/new")
    assert response.status_code == 200
    assert 'name="primary_domain"' in response.text
    assert '<option value="unknown" selected>' in response.text


def test_create_with_name_only_uses_unknown_defaults(client, db):
    response = post_vendor(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/vendors?msg=created"

    vendor = db.query(Vendor).one()
    assert vendor.name == "PayTrack"
    assert vendor.primary_domain is None
    assert vendor.handles_personal_info == TriState.UNKNOWN
    assert vendor.hosting_location == HostingLocation.UNKNOWN
    assert vendor.operator_agreement_status == AgreementStatus.UNKNOWN


def test_create_with_all_fields(client, db):
    response = post_vendor(
        client,
        name="  QuickSign  ",
        primary_domain="https://WWW.QuickSign.example/app",
        owner="Lerato Nkosi",
        handles_personal_info="yes",
        data_types="signatory names",
        hosting_location="outside_south_africa",
        operator_agreement_status="signed",
        operator_agreement_date="2026-03-10",
        certifications="SOC 2",
        last_reviewed="2026-04-01",
        next_review_due="2027-04-01",
        notes="E-signature tool",
    )
    assert response.status_code == 303
    vendor = db.query(Vendor).one()
    assert vendor.name == "QuickSign"
    assert vendor.primary_domain == "quicksign.example"
    assert vendor.handles_personal_info == TriState.YES
    assert vendor.hosting_location == HostingLocation.OUTSIDE_SOUTH_AFRICA
    assert vendor.operator_agreement_status == AgreementStatus.SIGNED
    assert vendor.operator_agreement_date == date(2026, 3, 10)
    assert vendor.next_review_due == date(2027, 4, 1)


def test_list_shows_success_banner(client):
    html = client.get("/vendors?msg=created").text
    assert "Vendor added." in html
    assert "Vendor added." not in client.get("/vendors?msg=anything").text


def test_empty_name_is_rejected_and_input_is_kept(client, db):
    response = post_vendor(client, name="   ", owner="Sipho")
    assert response.status_code == 422
    assert "This field is required." in response.text
    assert 'value="Sipho"' in response.text  # what the user typed is kept
    assert db.query(Vendor).count() == 0


def test_name_too_long_is_rejected(client, db):
    response = post_vendor(client, name="x" * 201)
    assert response.status_code == 422
    assert "Too long (maximum 200 characters)." in response.text
    assert db.query(Vendor).count() == 0


def test_malformed_domain_is_rejected(client, db):
    for bad in ["not a domain", "localhost", "1.2.3.4"]:
        response = post_vendor(client, primary_domain=bad)
        assert response.status_code == 422
        assert "Enter a valid domain" in response.text
    assert db.query(Vendor).count() == 0


def test_invalid_choice_and_date_are_rejected(client, db):
    response = post_vendor(client, handles_personal_info="maybe")
    assert response.status_code == 422
    assert "Choose one of the listed options." in response.text

    response = post_vendor(client, last_reviewed="13/10/2026")
    assert response.status_code == 422
    assert "Enter a valid date (YYYY-MM-DD)." in response.text
    assert db.query(Vendor).count() == 0


def test_duplicate_domain_is_rejected_but_blank_domains_are_fine(client, db):
    assert post_vendor(client, name="A", primary_domain="same.example").status_code == 303
    duplicate = post_vendor(client, name="B", primary_domain="WWW.same.example")
    assert duplicate.status_code == 422
    assert "Another vendor already uses this domain." in duplicate.text

    assert post_vendor(client, name="C").status_code == 303
    assert post_vendor(client, name="D").status_code == 303
    assert db.query(Vendor).count() == 3


def test_form_text_is_escaped_when_redisplayed(client):
    response = post_vendor(client, name="", owner='"><script>alert(1)</script>')
    assert response.status_code == 422
    assert "<script>alert(1)</script>" not in response.text


# ---- edit -----------------------------------------------------------------

def make_vendor(db, **fields):
    vendor = Vendor(name=fields.pop("name", "PayTrack"), **fields)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def test_edit_form_is_prefilled(client, db):
    vendor = make_vendor(
        db, primary_domain="paytrack.example", owner="Thandi",
        handles_personal_info=TriState.YES, next_review_due=date(2027, 6, 1),
    )
    html = client.get(f"/vendors/{vendor.id}/edit").text
    assert 'value="paytrack.example"' in html
    assert 'value="Thandi"' in html
    assert '<option value="yes" selected>' in html
    assert 'value="2027-06-01"' in html


def test_edit_updates_and_can_clear_fields(client, db):
    vendor = make_vendor(db, primary_domain="paytrack.example", owner="Thandi")
    response = client.post(
        f"/vendors/{vendor.id}/edit",
        data={"name": "PayTrack Ltd", "primary_domain": "paytrack.example", "owner": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/vendors?msg=updated"

    db.expire_all()
    vendor = db.get(Vendor, vendor.id)
    assert vendor.name == "PayTrack Ltd"
    assert vendor.owner is None
    assert vendor.primary_domain == "paytrack.example"  # keeping own domain is fine


def test_edit_cannot_take_another_vendors_domain(client, db):
    make_vendor(db, name="A", primary_domain="a.example")
    other = make_vendor(db, name="B", primary_domain="b.example")
    response = client.post(
        f"/vendors/{other.id}/edit",
        data={"name": "B", "primary_domain": "a.example"},
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Another vendor already uses this domain." in response.text
    db.expire_all()
    assert db.get(Vendor, other.id).primary_domain == "b.example"


def test_edit_validation_error_keeps_original_data(client, db):
    vendor = make_vendor(db, owner="Thandi")
    response = client.post(f"/vendors/{vendor.id}/edit", data={"name": ""})
    assert response.status_code == 422
    db.expire_all()
    assert db.get(Vendor, vendor.id).name == "PayTrack"


def test_missing_vendor_returns_404(client):
    assert client.get("/vendors/999/edit").status_code == 404
    assert client.post("/vendors/999/edit", data={"name": "x"}).status_code == 404
    assert client.get("/vendors/999/delete").status_code == 404
    assert client.post("/vendors/999/delete").status_code == 404


# ---- delete ---------------------------------------------------------------

def test_delete_confirmation_mentions_linked_applications(client, db):
    vendor = make_vendor(db)
    vendor.applications.extend([Application(name="One"), Application(name="Two")])
    db.commit()
    html = client.get(f"/vendors/{vendor.id}/delete").text
    assert "Delete PayTrack?" in html
    assert "2 linked applications will not be deleted" in html
    assert db.query(Vendor).count() == 1  # a GET never deletes


def test_delete_leaves_applications_unassigned(client, db):
    vendor = make_vendor(db)
    vendor.applications.append(Application(name="Payroll App"))
    db.commit()

    response = client.post(f"/vendors/{vendor.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/vendors?msg=deleted"

    db.expire_all()
    assert db.query(Vendor).count() == 0
    application = db.query(Application).one()
    assert application.vendor_id is None
