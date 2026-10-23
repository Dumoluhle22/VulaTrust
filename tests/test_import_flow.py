import re
from pathlib import Path

import app.routes.imports as imports_module
from app.models import Application, ImportBatch, Vendor
from app.pending_imports import PendingImports
from app.seed import load_vendors

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "apps.csv"
HEADER = "app_name,vendor_domain,source,user_count,scopes,privileged\n"


def upload(client, content: bytes | None = None, name: str = "apps.csv"):
    data = SAMPLE.read_bytes() if content is None else content
    return client.post("/import", files={"file": (name, data, "text/csv")})


def token_from(html: str) -> str:
    match = re.search(r'name="token" value="([^"]+)"', html)
    assert match, "no confirm form on the page"
    return match.group(1)


def confirm(client, token: str):
    return client.post("/import/confirm", data={"token": token}, follow_redirects=False)


# ---- preview ------------------------------------------------------------------

def test_preview_shows_match_counts_and_saves_nothing(client, db):
    load_vendors(db)
    html = upload(client).text
    assert "<strong>16</strong>Ready to import" in html
    assert "<strong>11</strong>Matched to a vendor" in html
    assert "<strong>5</strong>Left unassigned" in html
    assert "<strong>16</strong>New applications" in html
    assert "<strong>0</strong>Will be updated" in html
    assert "Confirm import of 16 applications" in html
    assert db.query(Application).count() == 0
    assert db.query(ImportBatch).count() == 0


def test_preview_explains_each_match_and_each_unassigned_row(client, db):
    load_vendors(db)
    html = upload(client).text
    assert "ClinicNotes <span class=\"muted\">(Subdomain)</span>" in html
    assert "ClinicNotes <span class=\"muted\">(Exact domain)</span>" in html
    assert "(No domain given)" in html
    assert "(No vendor uses this domain)" in html


def test_a_file_with_nothing_importable_has_no_confirm_button(client):
    html = upload(client, (HEADER + "Bad,a.example,dropbox,1,x,no\n").encode()).text
    assert "Nothing can be imported" in html
    assert "/import/confirm" not in html


# ---- confirm --------------------------------------------------------------------

def test_confirming_saves_everything_and_shows_the_batch(client, db):
    load_vendors(db)
    response = confirm(client, token_from(upload(client).text))
    assert response.status_code == 303
    assert response.headers["location"] == "/import/batches/1?msg=import_done"

    db.expire_all()
    assert db.query(Application).count() == 16
    assert db.query(ImportBatch).count() == 1

    page = client.get(response.headers["location"]).text
    assert "Import complete." in page
    assert "<strong>16</strong>New" in page
    assert "<strong>11</strong>Matched to a vendor" in page
    assert "<strong>5</strong>Left unassigned" in page
    assert "Applications from this import (16)" in page
    assert "Subdomain" in page


def test_imported_unassigned_apps_appear_on_the_unassigned_page(client, db):
    load_vendors(db)
    confirm(client, token_from(upload(client).text))
    html = client.get("/applications/unassigned").text
    assert "<strong>5</strong> applications need a vendor" in html
    assert "Quick Notes" in html


def test_a_token_works_only_once(client):
    token = token_from(upload(client).text)
    assert confirm(client, token).status_code == 303
    second = confirm(client, token)
    assert second.status_code == 422
    assert "expired or was already used" in second.text


def test_bad_and_missing_tokens_are_refused(client, db):
    for token in ["", "nonsense"]:
        response = confirm(client, token)
        assert response.status_code == 422
        assert "expired or was already used" in response.text
    assert db.query(Application).count() == 0


def test_an_expired_preview_is_refused(client, db, monkeypatch):
    now = {"t": 0.0}
    monkeypatch.setattr(
        imports_module, "pending_imports", PendingImports(ttl_seconds=60, clock=lambda: now["t"])
    )
    token = token_from(upload(client).text)
    now["t"] = 120
    assert confirm(client, token).status_code == 422
    assert db.query(Application).count() == 0


def test_reimporting_through_the_page_updates_instead_of_copying(client, db):
    load_vendors(db)
    confirm(client, token_from(upload(client).text))

    html = upload(client).text
    assert "<strong>0</strong>New applications" in html
    assert "<strong>16</strong>Will be updated" in html
    confirm(client, token_from(html))

    db.expire_all()
    assert db.query(Application).count() == 16
    assert db.query(ImportBatch).count() == 2


def test_import_that_fails_part_way_saves_nothing(client, db, monkeypatch):
    import app.importer as importer

    real = importer._write_row
    calls = {"n": 0}

    def flaky(session, batch, item):
        calls["n"] += 1
        if calls["n"] == 4:
            raise RuntimeError("boom")
        return real(session, batch, item)

    monkeypatch.setattr(importer, "_write_row", flaky)
    response = confirm(client, token_from(upload(client).text))
    assert response.status_code == 500
    assert "nothing was saved" in response.text
    db.expire_all()
    assert db.query(Application).count() == 0
    assert db.query(ImportBatch).count() == 0


# ---- history --------------------------------------------------------------------

def test_history_starts_empty_then_lists_batches_newest_first(client):
    assert "No imports yet." in client.get("/import/history").text
    confirm(client, token_from(upload(client, name="first.csv").text))
    confirm(client, token_from(upload(client, name="second.csv").text))
    html = client.get("/import/history").text
    assert html.index("second.csv") < html.index("first.csv")
    assert '<a href="/import/batches/1">View</a>' in html


def test_unknown_batch_returns_404(client):
    assert client.get("/import/batches/999").status_code == 404


def test_an_older_batch_lists_only_applications_it_still_owns(client):
    confirm(client, token_from(upload(client, name="first.csv").text))
    confirm(client, token_from(upload(client, name="second.csv").text))
    first = client.get("/import/batches/1").text
    assert "No applications are currently listed under this import." in first
    assert "Applications from this import (16)" in client.get("/import/batches/2").text


# ---- output safety --------------------------------------------------------------

def test_preview_and_batch_pages_escape_file_contents(client):
    evil = "<script>alert(1)</script>"
    content = (HEADER + f'{evil},"{evil}.example",csv,1,x,no\n').encode()
    preview = upload(client, content, name=f"{evil}.csv").text
    assert evil not in preview
    batch_page = client.get(confirm(client, token_from(preview)).headers["location"]).text
    assert evil not in batch_page
    assert "&lt;script&gt;" in batch_page


def test_vendor_names_are_escaped_in_the_preview(client, db):
    evil = "<script>alert(1)</script>"
    db.add(Vendor(name=evil, primary_domain="evil.example"))
    db.commit()
    html = upload(client, (HEADER + "App,evil.example,csv,1,x,no\n").encode()).text
    assert evil not in html
    assert "&lt;script&gt;" in html
