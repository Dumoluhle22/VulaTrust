# Testing

## Running the tests

```
python -m pytest                                   # everything
python -m pytest tests/test_scoring.py            # one file
python -m pytest -k "csv and formula"             # by name
python -m pytest --cov=app --cov-report=term-missing   # with coverage (needs requirements-dev.txt)
```

All tests use a temporary database, so they never touch `vulatrust.db`. Every test runs on a fixed date, **13 October 2026**, so overdue reviews and scores do not change from day to day. The CSRF check is switched off for most tests and switched on for the ones about it.

## Results at the time of writing

**333 tests, all passing. Line coverage of `app/`: 98%.** Every module is at 95% or above except `app/clock.py` (the one-line "today" function, replaced by a fixed date in tests) and `app/seed.py` (82%, the command-line entry point).

| Test file | Tests | What it covers |
|---|---|---|
| `test_models.py` | 9 | Defaults are unknown, unique domains, ON DELETE SET NULL, negative counts refused |
| `test_domains.py` | 21 | Cleaning and validating domains |
| `test_vendors.py` | 21 | Vendor add, edit, list, delete, validation and escaping |
| `test_vendor_rules.py` | 16 | Agreement and review date rules, including boundary days |
| `test_applications.py` | 25 | Application screens, linking and unlinking, vendor page |
| `test_assign.py` | 21 | Assign to an existing vendor, create a vendor from an application, matching again |
| `test_csv_import.py` | 40 | File and row checks, every rejection reason, line numbers, formula safety |
| `test_import_page.py` | 19 | The check page, refusals, unassigned page |
| `test_matching.py` | 14 | Exact, subdomain, most specific, ambiguous, no match |
| `test_pending_imports.py` | 5 | One-time, expiring, capped uploads |
| `test_importer.py` | 15 | Sample file results, re-import, manual links kept, all-or-nothing |
| `test_import_flow.py` | 15 | Preview, confirm, history, expiry, failure |
| `test_reviews.py` | 9 | Never reviewed, overdue, due today |
| `test_scoring.py` | 28 | Every factor, unknown handling, the sample vendors, the issue 17 scenarios |
| `test_vendor_score_pages.py` | 10 | Score, factors and notes on the vendor pages |
| `test_dashboard.py` | 21 | Counts and every dashboard list against the sample data |
| `test_security.py` | 38 | CSRF, headers, limits, injection, escaping, secrets |
| `test_app.py`, `test_sample_data.py` | 6 | Health check, home page, sample files |

## Tests tied to the sample data

`sample_data/README.md` lists the expected result of importing `apps.csv`: 23 rows read, 16 new, 11 matched, 5 unassigned, 6 rejected and 1 duplicate, and the expected score for each of the eight vendors. `test_csv_import.py`, `test_importer.py`, `test_scoring.py` and `test_dashboard.py` check these figures, so the documentation and the code cannot drift apart without a test failing.

## What the tests do not cover

- **How the pages look and feel.** No browser is used. Layout, colour and ease of use need the usability test (`docs/usability-test.md`).
- **Accessibility checks** beyond the fact that levels are written out and not shown by colour alone.
- **Real Google Workspace or Microsoft 365 data.** Direct import is not built. Only CSV files are tested.
- **Large scale.** The limit is 5,000 rows per file and nothing larger has been tried.
- **Several users at once.** The app is single-user.
- **The GitHub Actions workflow.** `.github/workflows/tests.yml` runs the same command as above, but it has not been run on GitHub.

## Adding a test

1. Put it in the file for that feature, using the `client` fixture for pages and the `db` fixture for the database.
2. Test the behaviour, including a boundary (the day before, the day of, the day after).
3. If it involves dates, do not read the real clock. Use the fixed date, or pass a date in.
4. If you add a form, the guard test in `test_security.py` will fail until the form includes `{% include "_csrf.html" %}`.
