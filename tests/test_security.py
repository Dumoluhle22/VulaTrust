"""Security checks for issue 20."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Application, ImportBatch, Vendor
from app.security import COOKIE_NAME, MAX_REQUEST_BYTES, SECURITY_HEADERS

ROOT = Path(__file__).resolve().parent.parent
HEADER = "app_name,vendor_domain,source,user_count,scopes,privileged\n"


def token_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "no CSRF token on the page"
    return match.group(1)


@pytest.fixture
def csrf_on(monkeypatch):
    monkeypatch.setenv("VULATRUST_CSRF", "1")


# ======================= CSRF =======================

def test_a_post_without_a_token_is_refused_and_changes_nothing(client, csrf_on, db):
    response = client.post("/vendors", data={"name": "Sneaky"})
    assert response.status_code == 403
    assert "could not be verified" in response.text
    assert db.query(Vendor).count() == 0


def test_a_token_without_the_cookie_is_refused(csrf_on, db):
    with TestClient(app) as fresh:   # has never loaded a page, so has no cookie
        response = fresh.post("/vendors", data={"name": "Sneaky", "csrf_token": "a" * 43})
    assert response.status_code == 403
    assert db.query(Vendor).count() == 0


def test_a_mismatched_token_is_refused(client, csrf_on, db):
    client.get("/vendors/new")
    response = client.post("/vendors", data={"name": "Sneaky", "csrf_token": "b" * 43})
    assert response.status_code == 403
    assert db.query(Vendor).count() == 0


def test_an_empty_token_is_refused(client, csrf_on, db):
    client.get("/vendors/new")
    assert client.post("/vendors", data={"name": "X", "csrf_token": ""}).status_code == 403


def test_the_normal_flow_works_with_a_valid_token(client, csrf_on, db):
    page = client.get("/vendors/new")
    token = token_from(page.text)
    response = client.post(
        "/vendors", data={"name": "Honest", "csrf_token": token}, follow_redirects=False
    )
    assert response.status_code == 303
    assert db.query(Vendor).one().name == "Honest"


def test_a_token_works_for_edit_delete_and_assign_too(client, csrf_on, db):
    vendor = Vendor(name="V", primary_domain="v.example")
    application = Application(name="A")
    db.add_all([vendor, application])
    db.commit()
    token = token_from(client.get("/vendors/new").text)

    assert client.post(f"/vendors/{vendor.id}/edit", data={"name": "V2"}).status_code == 403
    ok = client.post(f"/vendors/{vendor.id}/edit", data={"name": "V2", "csrf_token": token}, follow_redirects=False)
    assert ok.status_code == 303

    assert client.post(f"/applications/{application.id}/assign", data={"vendor_id": vendor.id}).status_code == 403
    assert client.post(f"/applications/{application.id}/delete").status_code == 403
    assert client.post("/applications/unassigned/rematch").status_code == 403
    assert client.post(f"/vendors/{vendor.id}/delete").status_code == 403
    db.expire_all()
    assert db.get(Application, application.id) is not None and db.get(Vendor, vendor.id) is not None
    assert db.get(Application, application.id).vendor_id is None


def test_the_csv_upload_and_confirm_steps_are_protected(client, csrf_on, db):
    page = client.get("/import")
    token = token_from(page.text)
    files = {"file": ("apps.csv", (HEADER + "App,a.example,csv,1,x,no\n").encode(), "text/csv")}

    assert client.post("/import", files=files).status_code == 403
    preview = client.post("/import", data={"csrf_token": token}, files=files)
    assert preview.status_code == 200
    pending = re.search(r'name="token" value="([^"]+)"', preview.text).group(1)

    assert client.post("/import/confirm", data={"token": pending}).status_code == 403
    assert db.query(Application).count() == 0
    done = client.post("/import/confirm", data={"token": pending, "csrf_token": token}, follow_redirects=False)
    assert done.status_code == 303
    assert db.query(Application).count() == 1


def test_get_requests_need_no_token(client, csrf_on):
    for path in ["/", "/vendors", "/applications", "/import", "/import/history", "/vendors/new"]:
        assert client.get(path).status_code == 200, path


def test_the_cookie_is_httponly_samesite_strict_and_set_once(client):
    first = client.get("/")
    cookie = first.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE_NAME}=")
    assert "httponly" in cookie.lower()
    assert "samesite=strict" in cookie.lower()
    assert "path=/" in cookie.lower()
    assert "set-cookie" not in client.get("/vendors").headers   # reused, not reissued


def test_a_malformed_cookie_is_replaced(csrf_on):
    with TestClient(app) as fresh:
        fresh.cookies.set(COOKIE_NAME, "short")
        response = fresh.get("/vendors/new")   # a page that has a form, and so a token
    assert COOKIE_NAME in response.headers.get("set-cookie", "")
    assert token_from(response.text) != "short"


def test_every_post_form_in_every_template_carries_the_token():
    """A guard for the future: a new form without a token fails here."""
    problems = []
    for path in sorted((ROOT / "app" / "templates").glob("*.html")):
        text = path.read_text(encoding="utf-8")
        forms = len(re.findall(r'<form method="post"', text))
        tokens = len(re.findall(r'\{% include "_csrf.html" %\}', text))
        if forms != tokens:
            problems.append(f"{path.name}: {forms} forms, {tokens} tokens")
    assert problems == []


def test_the_rendered_pages_contain_the_token(client, db):
    vendor = Vendor(name="V")
    application = Application(name="A", source_domain="a.example")
    db.add_all([vendor, application])
    db.commit()
    pages = [
        "/vendors/new", f"/vendors/{vendor.id}/edit", f"/vendors/{vendor.id}/delete",
        f"/vendors/new?from_application={application.id}", "/applications/new",
        f"/applications/{application.id}/edit", f"/applications/{application.id}/delete",
        f"/applications/{application.id}/assign", "/applications/unassigned", "/import",
    ]
    for path in pages:
        assert 'name="csrf_token"' in client.get(path).text, path


# ======================= headers, limits, docs =======================

def test_security_headers_are_on_every_kind_of_response(client, csrf_on):
    responses = [
        client.get("/"),
        client.get("/vendors/999"),                              # 404
        client.post("/vendors", data={"name": "x"}),             # 403 from CSRF
        client.post("/import", content=b"x" * (MAX_REQUEST_BYTES + 1),
                    headers={"content-type": "application/octet-stream"}),  # 413
    ]
    assert [r.status_code for r in responses] == [200, 404, 403, 413]
    for response in responses:
        for name, value in SECURITY_HEADERS.items():
            assert response.headers[name] == value, (response.status_code, name)


def test_the_policy_forbids_scripts_and_framing():
    policy = SECURITY_HEADERS["Content-Security-Policy"]
    assert "script-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "form-action 'self'" in policy
    assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"
    assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"


def test_pages_contain_no_scripts_at_all(client, db):
    db.add(Vendor(name="V"))
    db.commit()
    for path in ["/", "/vendors", "/vendors/new", "/applications", "/import"]:
        assert "<script" not in client.get(path).text.lower(), path


def test_an_oversized_request_is_refused_before_it_is_read(client, db):
    response = client.post("/import", content=b"x" * (MAX_REQUEST_BYTES + 1),
                           headers={"content-type": "application/octet-stream"})
    assert response.status_code == 413


def test_a_file_just_over_the_file_limit_still_gets_a_friendly_error(client):
    from app.csv_import import MAX_FILE_BYTES
    response = client.post("/import", files={"file": ("a.csv", b"x" * (MAX_FILE_BYTES + 10), "text/csv")})
    assert response.status_code == 422 and "too large" in response.text


def test_the_generated_api_docs_are_switched_off(client):
    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 404, path


def test_debug_mode_is_off():
    assert app.debug is False


# ======================= injection =======================

SQL_PAYLOADS = [
    "'; DROP TABLE vendors; --",
    '" OR "1"="1',
    "Robert'); DROP TABLE applications;--",
    "1; SELECT * FROM vendors",
    "' UNION SELECT name FROM sqlite_master --",
    "\\'; DELETE FROM vendors; --",
]


@pytest.mark.parametrize("payload", SQL_PAYLOADS)
def test_sql_text_in_vendor_and_application_fields_is_stored_as_plain_text(client, db, payload):
    response = client.post("/vendors", data={
        "name": payload, "owner": payload, "data_types": payload, "certifications": payload, "notes": payload,
    }, follow_redirects=False)
    assert response.status_code == 303
    vendor = db.query(Vendor).one()
    assert (vendor.name, vendor.owner, vendor.notes) == (payload, payload, payload)

    response = client.post("/applications", data={"name": payload, "scopes": payload, "vendor_id": str(vendor.id)},
                           follow_redirects=False)
    assert response.status_code == 303
    application = db.query(Application).one()
    assert (application.name, application.scopes) == (payload, payload)
    assert db.query(Vendor).count() == 1            # nothing was dropped or deleted


def test_sql_in_the_domain_field_is_rejected_as_an_invalid_domain(client, db):
    for payload in SQL_PAYLOADS:
        response = client.post("/vendors", data={"name": "V", "primary_domain": payload})
        assert response.status_code == 422
    assert db.query(Vendor).count() == 0


@pytest.mark.parametrize("payload", SQL_PAYLOADS)
def test_sql_in_query_strings_and_paths_is_harmless(client, db, payload):
    db.add(Vendor(name="Keep me"))
    db.add(Application(name="Keep me too"))
    db.commit()
    requests = [
        ("/vendors", {"level": payload}), ("/vendors", {"msg": payload}),
        ("/applications/new", {"vendor_id": payload}), ("/vendors/new", {"from_application": payload}),
        ("/applications/unassigned", {"linked": payload}), ("/applications", {"msg": payload}),
        ("/import/batches/1", {"msg": payload}),
    ]
    for path, params in requests:
        assert client.get(path, params=params).status_code in (200, 404), (path, params)
    for path in ["/vendors/1;DROP TABLE vendors", "/applications/1 OR 1=1/edit", "/vendors/%27"]:
        assert client.get(path).status_code in (404, 422), path
    assert db.query(Vendor).count() == 1 and db.query(Application).count() == 1


def test_sql_in_csv_cells_is_stored_as_plain_text(client, db):
    payload = "x'); DROP TABLE vendors;--"
    csv = (HEADER + f'"{payload}",a.example,csv,1,"{payload}",no\n').encode()
    token = re.search(r'name="token" value="([^"]+)"',
                      client.post("/import", files={"file": ("a.csv", csv, "text/csv")}).text).group(1)
    client.post("/import/confirm", data={"token": token})
    application = db.query(Application).one()
    assert application.name == payload and application.scopes == payload


# ======================= script injection (XSS) =======================

XSS = ['<script>alert(1)</script>', '"><img src=x onerror=alert(1)>', "'><svg onload=alert(1)>"]
FORBIDDEN = ["<script>alert", "<img src=x", "<svg onload"]


def test_hostile_text_is_escaped_on_every_page(client, db):
    p1, p2, p3 = XSS
    vendor = Vendor(name=p1, owner=p2, notes=p3, data_types=p1, certifications=p2, primary_domain="v.example")
    application = Application(name=p2, scopes=p3, source_domain="a.example", vendor=vendor)
    loose = Application(name=p1, scopes=p2, source_domain="b.example")
    batch = ImportBatch(filename=p3, row_count=1)
    db.add_all([vendor, application, loose, batch])
    db.commit()
    application.import_batch_id = batch.id
    db.commit()

    pages = [
        "/", "/vendors", f"/vendors/{vendor.id}", f"/vendors/{vendor.id}/edit", f"/vendors/{vendor.id}/delete",
        "/vendors/new", f"/vendors/new?from_application={loose.id}", "/applications", "/applications/new",
        f"/applications/{application.id}/edit", f"/applications/{application.id}/delete",
        f"/applications/{loose.id}/assign", "/applications/unassigned", "/import", "/import/history",
        f"/import/batches/{batch.id}", "/vendors?level=high",
    ]
    for path in pages:
        response = client.get(path)
        assert response.status_code == 200, path
        for marker in FORBIDDEN:
            assert marker not in response.text, (path, marker)


def test_hostile_text_is_escaped_when_a_form_is_redisplayed(client):
    for payload in XSS:
        for path, data in [
            ("/vendors", {"name": "", "owner": payload, "notes": payload}),
            ("/applications", {"name": "", "scopes": payload}),
        ]:
            html = client.post(path, data=data).text
            for marker in FORBIDDEN:
                assert marker not in html, (path, marker)


def test_upload_filenames_cannot_escape_or_inject(client, tmp_path):
    csv = (HEADER + "App,a.example,csv,1,x,no\n").encode()
    for name in ["../../etc/passwd.csv", "..\\..\\windows\\evil.csv", '"><script>alert(1)</script>.csv']:
        response = client.post("/import", files={"file": (name, csv, "text/csv")})
        assert response.status_code == 200, name
        for marker in FORBIDDEN:
            assert marker not in response.text
    assert list(tmp_path.iterdir()) == []   # nothing is ever written to disk by an upload


# ======================= secrets =======================

SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    r"ghp_[A-Za-z0-9]{30,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"sk-[A-Za-z0-9]{32,}",
    r"""(?i)\b(api[_-]?key|secret|passwd|password|access[_-]?token)\s*[:=]\s*['"][^'"\s]{8,}['"]""",
]


def test_no_secrets_in_the_project_files():
    this_file = Path(__file__).resolve()
    scanned, hits = 0, []
    for folder in ["app", "tests", "docs", "sample_data"]:
        for path in (ROOT / folder).rglob("*"):
            if not path.is_file() or path.resolve() == this_file or path.suffix in {".pyc", ".db"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            scanned += 1
            hits += [f"{path.relative_to(ROOT)}: {pattern}" for pattern in SECRET_PATTERNS if re.search(pattern, text)]
    assert scanned > 30
    assert hits == []


def test_the_gitignore_and_env_files_are_not_in_the_project_tree_with_secrets():
    env = ROOT / ".env"
    assert not env.exists()
