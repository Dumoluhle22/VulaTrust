from pathlib import Path

from app.csv_import import MAX_FILE_BYTES
from app.models import Application, Vendor

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "apps.csv"
HEADER = "app_name,vendor_domain,source,user_count,scopes,privileged\n"


def upload(client, content: bytes, name: str = "apps.csv"):
    return client.post("/import", files={"file": (name, content, "text/csv")})


# ---- the check page ---------------------------------------------------------

def test_import_page_loads_and_says_nothing_is_saved(client):
    response = client.get("/import")
    assert response.status_code == 200
    assert "nothing is saved until you confirm" in response.text
    assert 'enctype="multipart/form-data"' in response.text
    assert "app_name, vendor_domain, source, user_count, scopes, privileged" in response.text


def test_template_download(client):
    response = client.get("/import/template.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert response.text.startswith("app_name,vendor_domain,source,user_count,scopes,privileged")


def test_sample_file_report(client, db):
    response = upload(client, SAMPLE.read_bytes())
    assert response.status_code == 200
    html = response.text
    assert "<strong>23</strong>Rows read" in html
    assert "<strong>16</strong>Ready to import" in html
    assert "<strong>1</strong>Duplicates skipped" in html
    assert "<strong>6</strong>Rejected" in html
    assert "User count must be a whole number." in html
    assert "Source must be one of: manual, csv, google, microsoft." in html
    assert "App name is required." in html
    assert "'=1+1 Report Tool" in html or "&#39;=1+1 Report Tool" in html
    # checking a file must not save anything
    assert db.query(Application).count() == 0
    assert db.query(Vendor).count() == 0


def test_every_rejected_line_number_appears(client):
    html = upload(client, SAMPLE.read_bytes()).text
    for line in (19, 20, 21, 22, 23, 24):
        assert f"<tr><td>{line}</td>" in html


def test_preview_is_limited_to_twenty_rows(client):
    rows = "".join(f"App {i},a{i}.example,csv,1,x,no\n" for i in range(30))
    html = upload(client, (HEADER + rows).encode()).text
    assert "Showing the first 20." in html
    assert "App 19" in html
    assert "App 25" not in html


def test_header_only_file_explains_itself(client):
    html = upload(client, HEADER.encode()).text
    assert "header but no data rows" in html


# ---- refusals ---------------------------------------------------------------

def test_no_file_is_refused(client):
    response = client.post("/import")
    assert response.status_code == 422
    assert "Choose a CSV file to check." in response.text


def test_wrong_file_type_is_refused(client):
    response = upload(client, HEADER.encode(), "apps.xlsx")
    assert response.status_code == 422
    assert "Only .csv files are accepted." in response.text


def test_oversized_file_is_refused(client):
    response = upload(client, b"x" * (MAX_FILE_BYTES + 10))
    assert response.status_code == 422
    assert "too large" in response.text


def test_missing_columns_are_explained(client):
    response = upload(client, b"app_name,source\nApp,csv\n")
    assert response.status_code == 422
    assert "Missing required columns" in response.text


def test_binary_file_renamed_to_csv_is_refused(client):
    response = upload(client, b"MZ\x90\x00\x03\x00\x00\x00")
    assert response.status_code == 422
    assert "does not look like a text CSV" in response.text


# ---- output safety ----------------------------------------------------------

def test_file_contents_are_escaped_in_the_report(client):
    evil = '<script>alert(1)</script>'
    content = (
        HEADER
        + f'{evil},a.example,csv,1,"{evil}",no\n'
        + f'{evil},b.example,dropbox,1,x,no\n'
    )
    html = upload(client, content.encode()).text
    assert evil not in html
    assert "&lt;script&gt;" in html


def test_hostile_filename_is_escaped(client):
    html = upload(client, HEADER.encode(), '"><script>alert(1)</script>.csv').text
    assert "<script>alert(1)</script>" not in html


# ---- issue 8: unassigned applications page ---------------------------------

def test_unassigned_page_lists_only_unlinked_applications(client, db):
    vendor = Vendor(name="PayTrack")
    db.add_all([
        vendor,
        Application(name="Linked", vendor=vendor),
        Application(name="zeta loose"),
        Application(name="Alpha loose"),
    ])
    db.commit()
    html = client.get("/applications/unassigned").text
    assert "Linked" not in html
    assert html.index("Alpha loose") < html.index("zeta loose")
    assert "<strong>2</strong> applications need a vendor" in html


def test_unassigned_entries_link_to_the_assign_page(client, db):
    application = Application(name="Loose")
    db.add(application)
    db.commit()
    html = client.get("/applications/unassigned").text
    assert f'href="/applications/{application.id}/assign"' in html
    assert "Assign vendor" in html


def test_unassigned_singular_and_empty_states(client, db):
    assert "Every application is linked to a vendor." in client.get("/applications/unassigned").text
    db.add(Application(name="One"))
    db.commit()
    assert "<strong>1</strong> application needs a vendor" in client.get("/applications/unassigned").text


def test_unassigned_page_escapes_text(client, db):
    db.add(Application(name="<script>alert(1)</script>", scopes="<b>x</b>"))
    db.commit()
    html = client.get("/applications/unassigned").text
    assert "<script>alert(1)</script>" not in html
    assert "<b>x</b>" not in html


def test_home_count_links_to_the_unassigned_page(client, db):
    db.add(Application(name="Loose"))
    db.commit()
    html = client.get("/").text
    assert '<a class="card" href="/applications/unassigned"><strong>1</strong>Unassigned applications</a>' in html


def test_unassigned_route_is_not_mistaken_for_an_id(client):
    assert client.get("/applications/unassigned").status_code == 200
