# Security notes

VulaTrust is a **single-user prototype that runs on your own computer**. These notes say what is protected, how it is tested, and, just as important, what is not protected.

## Safe use

- Run it only on `127.0.0.1` (the default). Do **not** use `--host 0.0.0.0` and do not put it on the internet.
- The app has **no login**. Anyone who can open its address can read and change every record.
- Use synthetic data for development and demonstrations. Vendor owner names are personal information, so record as little as you need.

## What is protected, and how it is tested

| Risk | Protection | Where tested |
|---|---|---|
| **SQL injection** | All database access goes through SQLAlchemy with parameters. No SQL is built from user text. | `test_security.py`: injection strings in every text field, query string and path, and in CSV cells, are stored as plain text and nothing is dropped. |
| **Script injection (XSS)** | Jinja2 escapes all text. Pages contain no scripts. The Content-Security-Policy sets `script-src 'none'`. | `test_security.py`: hostile text in names, notes, scopes, filenames and domains is checked across 17 pages and on redisplayed forms. |
| **CSRF** (another site making your browser submit a form) | Every form carries a random token that must match a cookie (`SameSite=Strict`, `HttpOnly`). The check is applied to every POST by default. | `test_security.py`: posts with no token, no cookie, a wrong token and an empty token are refused. A guard test fails if any template form lacks the token. |
| **Malicious or oversized uploads** | `.csv` only, at most 1 MB and 5,000 rows, valid UTF-8, no binary content. Requests over about 1.25 MB are refused before being read. Files are never saved to disk or executed. | `test_csv_import.py`, `test_import_page.py`, `test_security.py` |
| **Spreadsheet formula injection** | A text cell starting with `=`, `+`, `-` or `@` gets an apostrophe added on import, so it cannot run as a formula if later opened in a spreadsheet. | `test_csv_import.py` |
| **Clickjacking** | `X-Frame-Options: DENY` and `frame-ancestors 'none'` | `test_security.py` |
| **Information leaks** | The generated API documentation pages are off, debug mode is off, and responses are marked `no-store`. | `test_security.py` |
| **Secrets in the repository** | There are none. `.env` and `*.db` are ignored by Git. | `test_security.py` scans the project files for common secret patterns. |
| **Half-finished imports** | An import saves every row or none (one transaction). | `test_importer.py`, `test_import_flow.py` |

## Known limitations (not protected)

1. **No authentication or authorisation.** The biggest gap. Adding login and roles is the first thing to build before any shared use.
2. **No HTTPS.** The cookie has no `Secure` flag because the app runs over plain HTTP locally. Behind HTTPS, set it.
3. **The CSRF token is a plain double-submit cookie.** It stops a foreign website, but not an attacker who can already set cookies for this site (for example from a sibling subdomain). Signed tokens would close that.
4. **No rate limiting** on any form or upload.
5. **No audit log.** Changes are not recorded.
6. **The database file is not encrypted.** Use disk encryption on the computer.
7. **The size limit trusts the `Content-Length` header.** A client sending a chunked body without it is not stopped by that check, although the file reader still stops at 1 MB.
8. **Uploaded files wait in memory** (up to 10, for 30 minutes) between preview and confirm, and are lost on restart.
9. **Dependencies are given as minimum versions** in `requirements.txt` and are not pinned or audited. Before publishing, pin versions and run `pip-audit`. This has not been done.
10. **Export is not built**, so there is no exported file to protect, but if you add CSV export you must neutralise formula characters in every cell.

## Checks to run before you submit

These look through your Git history, which the automated tests cannot see. In PowerShell, from the repository folder:

```powershell
# database or environment files that should never be committed
git ls-files | Select-String -Pattern "\.db$|\.env$"

# anything that looks like a secret anywhere in the history
git log --all -p | Select-String -Pattern "AKIA|PRIVATE KEY|password\s*=|secret\s*=|api_key"
```

Both should print nothing. If a secret was ever committed, changing the file is not enough: treat the secret as leaked and replace it.

Then run `python -m pytest tests/test_security.py`.

## Reporting a problem

See `CONTRIBUTING.md`. Please report security problems privately.
