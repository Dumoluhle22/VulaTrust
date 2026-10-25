from datetime import date

from app.models import Application, ApplicationSource, Vendor


def make_vendor(db, name="PayTrack", domain="paytrack.example"):
    vendor = Vendor(name=name, primary_domain=domain)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def make_app(db, name="Quick Notes", domain="quicknotes.example", **fields):
    application = Application(
        name=name, source_domain=domain, source=ApplicationSource.GOOGLE, user_count=7, **fields
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def assign(client, application, vendor_id):
    return client.post(
        f"/applications/{application.id}/assign", data={"vendor_id": vendor_id}, follow_redirects=False
    )


# ---- the assign page ----------------------------------------------------------------

def test_assign_page_shows_the_application_and_both_choices(client, db):
    make_vendor(db)
    application = make_app(db, scopes="docs read")
    html = client.get(f"/applications/{application.id}/assign").text
    assert "Assign a vendor to Quick Notes" in html
    assert "quicknotes.example" in html and "docs read" in html
    assert "<strong>Unassigned</strong>" in html
    assert "PayTrack (paytrack.example)" in html
    assert 'value=""' not in html.split("<select")[1].split("</select>")[0]  # no "None" option
    assert f'href="/vendors/new?from_application={application.id}"' in html


def test_assign_page_without_vendors_offers_only_creation(client, db):
    application = make_app(db)
    html = client.get(f"/applications/{application.id}/assign").text
    assert "There are no vendors yet." in html
    assert "<select" not in html
    assert "Create a new vendor" in html


def test_assign_page_404(client):
    assert client.get("/applications/999/assign").status_code == 404
    assert client.post("/applications/999/assign", data={"vendor_id": "1"}).status_code == 404


def test_assign_page_escapes_text(client, db):
    application = make_app(db, name="<script>alert(1)</script>", domain=None)
    html = client.get(f"/applications/{application.id}/assign").text
    assert "<script>alert(1)</script>" not in html


# ---- path 1: link to an existing vendor ----------------------------------------------

def test_linking_to_an_existing_vendor_records_a_manual_match(client, db):
    vendor = make_vendor(db)
    application = make_app(db)
    response = assign(client, application, str(vendor.id))
    assert response.status_code == 303
    assert response.headers["location"] == f"/vendors/{vendor.id}?msg=app_linked"

    db.expire_all()
    application = db.get(Application, application.id)
    assert application.vendor_id == vendor.id
    assert application.match_method == "manual"
    assert "Application linked to this vendor." in client.get(response.headers["location"]).text


def test_the_unassigned_count_goes_down_after_linking(client, db):
    vendor = make_vendor(db)
    first, second = make_app(db, "One"), make_app(db, "Two", "two.example")
    assert "<strong>2</strong> applications need a vendor" in client.get("/applications/unassigned").text
    assign(client, first, str(vendor.id))
    page = client.get("/applications/unassigned").text
    assert "<strong>1</strong> application needs a vendor" in page
    assert "One" not in page.split("<tbody>")[1]
    assert "<strong>1</strong>Unassigned applications</a>" in client.get("/").text
    assign(client, second, str(vendor.id))
    assert "Every application is linked to a vendor." in client.get("/applications/unassigned").text


def test_invalid_vendor_choices_are_refused_and_change_nothing(client, db):
    make_vendor(db)
    application = make_app(db)
    for bad in ["", "999", "abc", "-1", "1; DROP TABLE vendors", "9" * 30]:
        response = assign(client, application, bad)
        assert response.status_code == 422, bad
        assert "Choose a vendor from the list." in response.text, bad
    db.expire_all()
    assert db.get(Application, application.id).vendor_id is None
    assert db.query(Vendor).count() == 1


def test_an_application_can_be_moved_to_another_vendor(client, db):
    first, second = make_vendor(db, "A", "a.example"), make_vendor(db, "B", "b.example")
    application = make_app(db, vendor=first, match_method="exact_domain")
    html = client.get(f"/applications/{application.id}/assign").text
    assert f'<option value="{first.id}" selected>' in html
    assign(client, application, str(second.id))
    db.expire_all()
    application = db.get(Application, application.id)
    assert (application.vendor_id, application.match_method) == (second.id, "manual")


# ---- path 2: create a vendor from the application -----------------------------------------

def test_new_vendor_form_is_prefilled_from_the_application(client, db):
    application = make_app(db)
    html = client.get(f"/vendors/new?from_application={application.id}").text
    assert 'value="Quick Notes"' in html
    assert 'value="quicknotes.example"' in html
    assert f'name="from_application" value="{application.id}"' in html
    assert "This vendor will be linked to the application" in html
    assert "main domain and not a subdomain" in html


def test_creating_a_vendor_from_an_application_links_it(client, db):
    application = make_app(db)
    response = client.post(
        "/vendors",
        data={"name": "QuickNotes Ltd", "primary_domain": "quicknotes.example",
              "from_application": str(application.id)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    vendor = db.query(Vendor).one()
    assert response.headers["location"] == f"/vendors/{vendor.id}?msg=created_linked"

    db.expire_all()
    application = db.get(Application, application.id)
    assert application.vendor_id == vendor.id
    assert application.match_method == "manual"
    page = client.get(response.headers["location"]).text
    assert "Vendor added, and the application is now linked to it." in page
    assert "Quick Notes" in page.split("Applications (")[1]
    assert "Every application is linked to a vendor." in client.get("/applications/unassigned").text


def test_a_failed_vendor_form_keeps_the_link_and_changes_nothing(client, db):
    application = make_app(db)
    response = client.post(
        "/vendors",
        data={"name": "", "primary_domain": "quicknotes.example", "from_application": str(application.id)},
    )
    assert response.status_code == 422
    assert f'name="from_application" value="{application.id}"' in response.text
    assert "This vendor will be linked to the application" in response.text
    db.expire_all()
    assert db.query(Vendor).count() == 0
    assert db.get(Application, application.id).vendor_id is None


def test_a_duplicate_domain_leaves_the_application_unassigned(client, db):
    make_vendor(db, "Existing", "quicknotes.example")
    application = make_app(db)
    response = client.post(
        "/vendors",
        data={"name": "Copy", "primary_domain": "quicknotes.example", "from_application": str(application.id)},
    )
    assert response.status_code == 422
    assert "Another vendor already uses this domain." in response.text
    db.expire_all()
    assert db.get(Application, application.id).vendor_id is None
    assert db.query(Vendor).count() == 1


def test_bad_application_ids_are_ignored(client, db):
    other = make_vendor(db, "Other", "other.example")
    linked = make_app(db, "Linked", vendor=other, match_method="exact_domain")
    for bad in ["999", "abc", "", "-5", "1 OR 1=1", "9" * 30, str(linked.id)]:
        response = client.post(
            "/vendors",
            data={"name": f"Vendor {abs(hash(bad)) % 1000}", "from_application": bad},
            follow_redirects=False,
        )
        assert response.status_code == 303, bad
        assert response.headers["location"] == "/vendors?msg=created", bad
    db.expire_all()
    assert db.get(Application, linked.id).vendor_id == other.id   # never relinked
    assert db.get(Application, linked.id).match_method == "exact_domain"


def test_prefill_ignores_an_already_linked_or_missing_application(client, db):
    vendor = make_vendor(db)
    linked = make_app(db, "Linked", vendor=vendor)
    for raw in [str(linked.id), "999", "abc"]:
        html = client.get(f"/vendors/new?from_application={raw}").text
        assert "This vendor will be linked" not in html
        assert 'name="from_application"' not in html


def test_the_prefilled_name_is_escaped(client, db):
    application = make_app(db, name='"><script>alert(1)</script>', domain=None)
    html = client.get(f"/vendors/new?from_application={application.id}").text
    assert "<script>alert(1)</script>" not in html


# ---- matching again ------------------------------------------------------------------------

def test_matching_again_links_applications_to_vendors_added_since(client, db):
    exact = make_app(db, "Exact", "paytrack.example")
    sub = make_app(db, "Sub", "app.paytrack.example")
    nothing = make_app(db, "Nothing", "elsewhere.example")
    no_domain = make_app(db, "NoDomain", None)
    vendor = make_vendor(db)

    response = client.post("/applications/unassigned/rematch", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/applications/unassigned?linked=2"

    db.expire_all()
    assert db.get(Application, exact.id).vendor_id == vendor.id
    assert db.get(Application, exact.id).match_method == "exact_domain"
    assert db.get(Application, sub.id).match_method == "subdomain"
    assert db.get(Application, nothing.id).vendor_id is None
    assert db.get(Application, no_domain.id).vendor_id is None
    assert "2 applications were linked to a vendor by domain." in client.get(response.headers["location"]).text


def test_matching_again_never_touches_linked_applications(client, db):
    a, b = make_vendor(db, "A", "a.example"), make_vendor(db, "B", "b.example")
    manual = make_app(db, "Manual", "b.example", vendor=a, match_method="manual")
    client.post("/applications/unassigned/rematch")
    db.expire_all()
    assert db.get(Application, manual.id).vendor_id == a.id
    assert db.get(Application, manual.id).match_method == "manual"


def test_matching_again_with_no_matches_says_so(client, db):
    make_app(db, "Nothing", "elsewhere.example")
    response = client.post("/applications/unassigned/rematch", follow_redirects=False)
    assert response.headers["location"].endswith("linked=0")
    page = client.get(response.headers["location"]).text
    assert "No unassigned application matched a vendor's domain." in page


def test_the_singular_message(client, db):
    make_vendor(db)
    make_app(db, "One", "paytrack.example")
    page = client.get(client.post("/applications/unassigned/rematch", follow_redirects=False).headers["location"]).text
    assert "1 application was linked to a vendor by domain." in page


def test_the_match_again_button_only_shows_when_it_could_help(client, db):
    assert "Match again" not in client.get("/applications/unassigned").text   # nothing unassigned
    make_app(db, "NoDomain", None)
    assert "Match again" not in client.get("/applications/unassigned").text   # no domain to match on
    make_app(db, "HasDomain", "x.example")
    assert "Match again using current vendors" in client.get("/applications/unassigned").text


def test_junk_in_the_linked_parameter_is_ignored(client):
    for junk in ["abc", "-1", "1.5", "9" * 30, "<script>", ""]:
        html = client.get("/applications/unassigned", params={"linked": junk}).text
        assert "were linked to a vendor" not in html and "was linked to a vendor" not in html
        assert "<script>" not in html
