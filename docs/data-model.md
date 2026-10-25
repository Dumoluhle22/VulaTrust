# Data model

Three tables, defined in `app/models.py` with SQLAlchemy. The database is created automatically on first run (`Base.metadata.create_all`). There is no migration tool: if the tables change, delete `vulatrust.db` and start again.

```
vendors 1 ---- * applications * ---- 1 import_batches
```

An application may have **no vendor** (it is "unassigned") and may have **no import batch** (it was typed in by hand).

## Safe defaults

Fields about a vendor's safeguards use **yes / no / unknown** (or a list ending in `unknown`), and the default is always **unknown**. A missing answer must never be stored or shown as "no".

## vendors

| Field | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| name | text (200) | Required |
| primary_domain | text (255) | Optional and **unique**, so domain matching is never ambiguous. Stored cleaned: lowercase, no `www.`, no protocol or path. |
| owner | text (200) | Person responsible for the relationship |
| handles_personal_info | yes / no / unknown | Default unknown |
| data_types | text | Free text |
| hosting_location | south_africa / outside_south_africa / unknown | Default unknown |
| operator_agreement_status | none / requested / signed / unknown | Default unknown |
| operator_agreement_date | date | Required when signed, forbidden otherwise, never in the future |
| certifications | text | Free text, for example ISO 27001 |
| last_reviewed | date | Not in the future |
| next_review_due | date | Not before last_reviewed |
| notes | text | Free text |
| created_at | datetime | UTC |

## applications

| Field | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| name | text (200) | Required |
| vendor_id | integer, nullable | Foreign key to vendors. **ON DELETE SET NULL**: deleting a vendor leaves its applications unassigned. |
| import_batch_id | integer, nullable | Foreign key to import_batches. Null for hand-entered applications. |
| source | manual / csv / google / microsoft | Where the application was found |
| discovered_at | datetime | When it first appeared |
| user_count | integer | 0 or more (database check) |
| scopes | text | Access it has. Imports limit it to 500 characters. |
| privileged | yes / no / unknown | Broad access such as a full mailbox or all files. Default unknown. |
| match_method | text, nullable | How the vendor link was made: `exact_domain`, `subdomain` or `manual`. Null when unlinked. |
| source_domain | text, nullable | The cleaned domain from the import file. Used to recognise the same application on re-import and to prefill a new vendor. |

## import_batches

One row per confirmed import.

| Field | Notes |
|---|---|
| id, filename, source, imported_at | Which file, and when (UTC) |
| row_count | Rows read from the file |
| created_count, updated_count | New applications versus ones updated by a re-import |
| matched_count, unassigned_count | Rows linked to a vendor versus left unassigned |
| rejected_count, duplicate_count | Rows that failed checks, and duplicates skipped |

## Code layout

| Module | Responsibility |
|---|---|
| `app/main.py` | Creates the app, registers routes, middleware and the dashboard page |
| `app/database.py`, `app/models.py` | Database connection and tables |
| `app/schemas.py` | Pydantic validation for the vendor and application forms, plus the date rules |
| `app/domains.py` | Cleaning and checking domain names |
| `app/csv_import.py` | Checks an uploaded CSV. Reads only, never saves. |
| `app/matching.py` | Matches a domain to a vendor |
| `app/importer.py` | Plans an import, then saves it in one transaction |
| `app/pending_imports.py` | Holds an uploaded file between preview and confirm |
| `app/reviews.py` | Review status (never reviewed, overdue, scheduled) |
| `app/scoring.py` | The risk score. Pure: no database, web or clock. |
| `app/dashboard.py` | Builds the dashboard lists |
| `app/security.py` | CSRF tokens, security headers, request size limit |
| `app/routes/` | The vendor, application and import screens |
| `app/templates/` | HTML pages. Jinja2 escapes all text automatically. |
| `app/seed.py` | Loads the sample vendors |
