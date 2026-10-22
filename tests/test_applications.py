from app.models import Application, ApplicationSource, TriState, Vendor


def post_app(client, **fields):
    data = {"name": "Payroll App"}
    data.update(fields)
    return client.post("/applications", data=data, follow_redirects=False)


def make_vendor(db, name="PayTrack", domain="paytrack.example"):
    vendor = Vendor(name=name, primary_domain=domain)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def make_app(db, **fields):
    application = Application(name=fields.pop("name", "Payroll App"), **fields)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


# ---- list -----------------------------------------------------------------

def test_empty_list_shows_message(client):
    response = client.get("/applications")
    assert response.status_code == 200
    assert "No applications yet" in response.text


def test_list_shows_columns_sorted_with_unassigned(client, db):
    vendor = make_vendor(db)
    make_app(db, name="zeta app", vendor=vendor, source=ApplicationSource.GOOGLE,
             user_count=12, privileged=TriState.YES)
    make_app(db, name="Alpha app")
    html = client.get("/applications").text

    assert html.index("Alpha app") < html.index("zeta app")
    assert "<strong>Unassigned</strong>" in html
    assert f'<a href="/vendors/{vendor.id}">PayTrack</a>' in html
    assert "Google Workspace" in html
    assert "<td>12</td>" in html
    assert "<td>Yes</td>" in html
    assert "<td>Unknown</td>" in html  # the unassigned app never had privileged set


def test_list_escapes_user_text(client, db):
    make_app(db, name="<script>alert(1)</script>")
    html = client.get("/applications").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# ---- create ---------------------------------------------------------------

def test_new_form_offers_none_and_all_vendors(client, db):
    make_vendor(db, "PayTrack", "paytrack.example")
    make_vendor(db, "Plain Co", None)
    html = client.get("/applications/new").text
    assert '<option value="" selected>None (unassigned)</option>' in html
    assert "PayTrack (paytrack.example)" in html
    assert ">Plain Co<" in html


def test_new_form_can_preselect_a_vendor(client, db):
    vendor = make_vendor(db)
    html = client.get(f"/applications/new?vendor_id={vendor.id}").text
    assert f'<option value="{vendor.id}" selected>' in html


def test_create_with_name_only_is_unassigned_with_safe_defaults(client, db):
    response = post_app(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/applications?msg=app_created"

    application = db.query(Application).one()
    assert application.vendor_id is None
    assert application.match_method is None
    assert application.source == ApplicationSource.MANUAL
    assert application.user_count == 0
    assert application.privileged == TriState.UNKNOWN


def test_create_linked_to_vendor_goes_to_vendor_page(client, db):
    vendor = make_vendor(db)
    response = post_app(
        client, vendor_id=str(vendor.id), source="google", user_count="7",
        scopes="calendar read/write", privileged="no",
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/vendors/{vendor.id}?msg=app_created"

    application = db.query(Application).one()
    assert application.vendor_id == vendor.id
    assert application.match_method == "manual"
    assert application.source == ApplicationSource.GOOGLE
    assert application.user_count == 7
    assert application.scopes == "calendar read/write"
    assert application.privileged == TriState.NO


def test_empty_name_rejected_and_input_kept(client, db):
    response = post_app(client, name="  ", scopes="files read")
    assert response.status_code == 422
    assert "This field is required." in response.text
    assert "files read" in response.text
    assert db.query(Application).count() == 0


def test_bad_numbers_are_rejected(client, db):
    cases = {
        "-3": "Must be 0 or more.",
        "abc": "Enter a whole number.",
        "12.5": "Enter a whole number.",
        "1000001": "Must be 1000000 or less.",
    }
    for value, message in cases.items():
        response = post_app(client, user_count=value)
        assert response.status_code == 422, value
        assert message in response.text, value
    assert db.query(Application).count() == 0


def test_bad_choices_and_lengths_are_rejected(client, db):
    assert "Choose one of the listed options." in post_app(client, source="dropbox").text
    assert "Choose one of the listed options." in post_app(client, privileged="maybe").text
    assert "Too long (maximum 500 characters)." in post_app(client, scopes="x" * 501).text
    assert "Too long (maximum 200 characters)." in post_app(client, name="x" * 201).text
    assert db.query(Application).count() == 0


def test_unknown_or_tampered_vendor_is_rejected(client, db):
    for bad in ["999", "abc"]:
        response = post_app(client, vendor_id=bad)
        assert response.status_code == 422, bad
        assert "Choose a vendor from the list." in response.text, bad
    assert db.query(Application).count() == 0


def test_form_text_is_escaped_when_redisplayed(client):
    response = post_app(client, name="", scopes='"></textarea><script>alert(1)</script>')
    assert response.status_code == 422
    assert "<script>alert(1)</script>" not in response.text


# ---- edit: linking and unlinking -------------------------------------------

def test_edit_form_is_prefilled(client, db):
    vendor = make_vendor(db)
    application = make_app(
        db, vendor=vendor, source=ApplicationSource.MICROSOFT,
        user_count=40, scopes="profile read", privileged=TriState.NO,
    )
    html = client.get(f"/applications/{application.id}/edit").text
    assert 'value="Payroll App"' in html
    assert f'<option value="{vendor.id}" selected>' in html
    assert '<option value="microsoft" selected>' in html
    assert 'value="40"' in html
    assert "profile read" in html
    assert '<option value="no" selected>' in html


def test_edit_can_link_an_unassigned_application(client, db):
    vendor = make_vendor(db)
    application = make_app(db)
    response = client.post(
        f"/applications/{application.id}/edit",
        data={"name": "Payroll App", "vendor_id": str(vendor.id)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/vendors/{vendor.id}?msg=app_updated"
    db.expire_all()
    application = db.get(Application, application.id)
    assert application.vendor_id == vendor.id
    assert application.match_method == "manual"


def test_edit_can_unlink_an_application(client, db):
    vendor = make_vendor(db)
    application = make_app(db, vendor=vendor, match_method="exact_domain")
    response = client.post(
        f"/applications/{application.id}/edit",
        data={"name": "Payroll App", "vendor_id": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/applications?msg=app_updated"
    db.expire_all()
    application = db.get(Application, application.id)
    assert application.vendor_id is None
    assert application.match_method is None


def test_edit_that_keeps_the_vendor_keeps_the_match_method(client, db):
    vendor = make_vendor(db)
    application = make_app(db, vendor=vendor, match_method="exact_domain")
    client.post(
        f"/applications/{application.id}/edit",
        data={"name": "Renamed", "vendor_id": str(vendor.id), "user_count": "9"},
    )
    db.expire_all()
    application = db.get(Application, application.id)
    assert application.name == "Renamed"
    assert application.user_count == 9
    assert application.match_method == "exact_domain"


def test_edit_can_move_between_vendors(client, db):
    first = make_vendor(db, "A", "a.example")
    second = make_vendor(db, "B", "b.example")
    application = make_app(db, vendor=first, match_method="exact_domain")
    client.post(
        f"/applications/{application.id}/edit",
        data={"name": "Payroll App", "vendor_id": str(second.id)},
    )
    db.expire_all()
    application = db.get(Application, application.id)
    assert application.vendor_id == second.id
    assert application.match_method == "manual"


def test_failed_edit_changes_nothing(client, db):
    vendor = make_vendor(db)
    application = make_app(db, vendor=vendor, user_count=5)
    response = client.post(
        f"/applications/{application.id}/edit",
        data={"name": "", "vendor_id": "", "user_count": "99"},
    )
    assert response.status_code == 422
    db.expire_all()
    application = db.get(Application, application.id)
    assert application.name == "Payroll App"
    assert application.vendor_id == vendor.id
    assert application.user_count == 5


def test_missing_application_returns_404(client):
    assert client.get("/applications/999/edit").status_code == 404
    assert client.post("/applications/999/edit", data={"name": "x"}).status_code == 404
    assert client.get("/applications/999/delete").status_code == 404
    assert client.post("/applications/999/delete").status_code == 404


# ---- delete ---------------------------------------------------------------

def test_delete_needs_confirmation_and_keeps_the_vendor(client, db):
    vendor = make_vendor(db)
    application = make_app(db, vendor=vendor)

    page = client.get(f"/applications/{application.id}/delete")
    assert "Delete Payroll App?" in page.text
    assert db.query(Application).count() == 1  # a GET never deletes

    response = client.post(f"/applications/{application.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/vendors/{vendor.id}?msg=app_deleted"
    db.expire_all()
    assert db.query(Application).count() == 0
    assert db.query(Vendor).count() == 1


# ---- vendor detail page ---------------------------------------------------

def test_vendor_page_lists_its_applications_only(client, db):
    vendor = make_vendor(db)
    other = make_vendor(db, "Other", "other.example")
    make_app(db, name="Mine B", vendor=vendor, user_count=3)
    make_app(db, name="Mine A", vendor=vendor)
    make_app(db, name="Not mine", vendor=other)
    make_app(db, name="Floating")

    html = client.get(f"/vendors/{vendor.id}").text
    assert "Applications (2)" in html
    assert html.index("Mine A") < html.index("Mine B")
    assert "Not mine" not in html
    assert "Floating" not in html
    assert f"/applications/new?vendor_id={vendor.id}" in html


def test_vendor_page_shows_unknown_values_and_empty_state(client, db):
    vendor = make_vendor(db, "Mystery", None)
    html = client.get(f"/vendors/{vendor.id}").text
    assert "No applications yet for this vendor." in html
    assert html.count("Unknown") >= 3
    assert "not set" in html


def test_vendor_page_shows_banner_and_escapes_text(client, db):
    vendor = Vendor(name="<b>Bold</b>", notes="<script>alert(1)</script>")
    db.add(vendor)
    db.commit()
    html = client.get(f"/vendors/{vendor.id}?msg=app_created").text
    assert "Application added." in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;b&gt;Bold&lt;/b&gt;" in html


def test_vendor_page_404_and_list_links_to_it(client, db):
    assert client.get("/vendors/999").status_code == 404
    vendor = make_vendor(db)
    assert f'<a href="/vendors/{vendor.id}">PayTrack</a>' in client.get("/vendors").text


def test_new_vendor_route_is_not_mistaken_for_an_id(client):
    assert client.get("/vendors/new").status_code == 200
