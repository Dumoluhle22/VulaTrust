# Sample data (synthetic)

All names, people and domains here are fictional. Domains use the reserved `.example` ending, so none of them can belong to a real company.

| File | What it is |
|---|---|
| `vendors.csv` | 8 fictional vendors covering high, medium and low scores. Load with `python -m app.seed` (safe to run twice). |
| `apps.csv` | 23 import rows: matching cases, unassigned cases, one duplicate, six invalid rows and one spreadsheet-formula row. |

**Reference date for all expected results: 13 October 2026.** Overdue reviews and scores depend on today's date, so tests must pass this date in and never read the system clock.

## Rules these results assume

These are proposals for issues 9, 10, 11 and 15. If you decide differently, change the rule and update the expected results to match.

1. **Domain normalisation:** lowercase, remove `http(s)://`, any path or port, and a leading `www.`.
2. **Matching:** an app matches a vendor when its domain equals the vendor's domain or is a subdomain of it (`app.clinicnotes.example` matches `clinicnotes.example`). A blank or unknown domain stays unassigned.
3. **Duplicates:** two rows with the same app name (ignoring upper or lower case), normalised domain and source count as one application. Only valid rows can be duplicates.
4. **Rejected rows:** blank app name, user count that is not a whole number, is negative or is over 1,000,000, source not in manual/csv/google/microsoft, privileged not yes/no/unknown, scopes over 500 characters, app name over 200 characters, or a row with a different number of cells from the header. Every problem in a row is reported, not just the first.
5. **Formula safety:** a cell starting with `=`, `+`, `-` or `@` is accepted but prefixed with an apostrophe so a spreadsheet will not run it.
6. **Vendor-level inputs:** users are the **sum** across the vendor's applications. Privileged is **yes** if any application is yes, otherwise **unknown** if any is unknown. A vendor with **no applications** recorded is also treated as **unknown**, so it scores half the privileged points and is marked unverified.
7. **Unknown inputs** add half a factor's points. The total is rounded half up to a whole number at the end.
8. **Blank cells:** a blank source becomes `csv`, a blank privileged becomes `unknown` (never `no`), and a blank user count becomes 0. Source and privileged are accepted in any letter case.
9. **Invalid domain:** a domain that is filled in but not valid does not reject the row. The application is kept, left unassigned, and a warning is shown.
10. **File rules (issue 9):** `.csv` only, UTF-8 text (Excel's BOM is fine), at most 1 MB and 5,000 rows, comma or semicolon separated. The first row must hold the six column names in any order and any letter case, and extra columns are ignored. Line numbers count the header as line 1.
11. **Matching (issue 10):** an application matches a vendor when its cleaned domain equals the vendor's domain (`exact_domain`) or ends with a dot plus the vendor's domain (`subdomain`). Only whole labels count, so `notpaytrack.example` does not match `paytrack.example`. If several vendor domains fit, the most specific one wins. A blank domain, an unknown domain, or a domain claimed by more than one vendor is left unassigned and never guessed.
12. **Re-import (issue 11):** the same application is recognised by app name (ignoring case), cleaned domain and source. A re-import updates users, access and privileged from the file and creates no copies. A vendor link made by hand is never changed by an import, and hand-entered applications are never touched.
13. **All or nothing:** an import saves every valid row or none of them.
14. **Agreement dates (issue 13):** a signing date is required when the status is `signed`, may not be in the future, and may not be entered for any other status.
15. **Review dates (issue 14):** last reviewed may not be in the future, and next review due may not be before the last review. A vendor is **overdue** when its next review date has passed (a review due today is not overdue) or when it was never reviewed. A vendor that was reviewed but has no next date is shown as "no next review date" and is not counted as overdue.
16. **Scores use today's date.** The expected results in this file use 13 October 2026. The running app uses the real date, so a vendor's overdue status can change over time.

## Expected import result for `apps.csv`

| Measure | Expected |
|---|---|
| Rows read | 23 |
| Rejected | 6 |
| Duplicates skipped | 1 |
| Applications imported | 16 |
| Matched to a vendor | 11 |
| Unassigned | 5 |

### Row by row

| Row | App | Expected outcome | What it tests |
|---|---|---|---|
| 1 | PayTrack Payroll | Matched to PayTrack | Exact domain |
| 2 | PayTrack Mobile | Matched to PayTrack | Uppercase domain |
| 3 | ClinicNotes Web | Matched to ClinicNotes | `www.` prefix |
| 4 | QuickSign | Matched to QuickSign | Protocol and path in the domain |
| 5 | ChatBridge Desktop | Matched to ChatBridge | Unknown privileged value |
| 6 | Brightlearn LMS | Matched to Brightlearn LMS | Large user count |
| 7 | MailBlast | Matched to MailBlast | Plain match |
| 8 | DesignHub | Matched to DesignHub | Source is csv |
| 9 | LedgerLite | Matched to LedgerLite | Privileged yes |
| 10 | ClinicNotes Reports | Matched to ClinicNotes | Subdomain |
| 11 | DesignHub Plugin | Matched to DesignHub | Second app for one vendor |
| 12 | Mystery PDF Tool | Unassigned | Blank domain |
| 13 | Quick Notes | Unassigned | Domain with no vendor |
| 14 | Survey Maker | Unassigned | Domain with no vendor |
| 15 | Calendar Sync Pro | Unassigned | Domain with no vendor |
| 16 | =1+1 Report Tool | Imported as `'=1+1 Report Tool`, unassigned | Formula characters |
| 17 | PayTrack Payroll (again) | Skipped as duplicate | Duplicate row |
| 18 | Bad Count App | Rejected | User count is "abc" |
| 19 | Negative Count App | Rejected | User count is -3 |
| 20 | Bad Source App | Rejected | Source is "dropbox" |
| 21 | Bad Privileged App | Rejected | Privileged is "maybe" |
| 22 | Long Scopes App | Rejected | Scopes over 500 characters |
| 23 | (blank name) | Rejected | Missing app name |

## Expected vendor scores (after importing `apps.csv`)

| Vendor | Apps | Users | Points | Level | Why |
|---|---|---|---|---|---|
| PayTrack | 2 | 5 | 5 | Low | Only the 5-user rule applies (3 + 2 summed) |
| ClinicNotes | 2 | 9 | 85 | High | No agreement 35, privileged 20, overdue 15, outside SA 10, users 5 |
| QuickSign | 1 | 6 | 15 | Low | Outside SA 10, users 5 |
| ChatBridge | 1 | 12 | 68 (67.5 before rounding) | Medium | Unknown personal info and agreement 17.5, unknown privileged 10, no owner 15, never reviewed 15, unknown hosting 5, users 5 |
| Brightlearn LMS | 1 | 40 | 40 | Medium | Agreement only requested 35, users 5. Sits exactly on the boundary |
| MailBlast | 1 | 2 | 60 | Medium | No agreement 35, overdue 15, outside SA 10 |
| DesignHub | 2 | 11 | 15 | Low | No personal information. Outside SA 10, users 5 |
| LedgerLite | 1 | 3 | 50 | Medium | Privileged 20, no owner 15, overdue 15 |

Level cut-offs: 70 or more is high, 40 to 69 is medium, below 40 is low.

## Expected dashboard results

- **Unassigned applications:** 5
- **High-level vendors:** 1 (ClinicNotes)
- **Handles or may handle personal information with no signed agreement:** ClinicNotes, ChatBridge, Brightlearn LMS, MailBlast
- **Overdue or never-reviewed vendors:** ClinicNotes, ChatBridge (never reviewed), MailBlast, LedgerLite
- **Vendors with no owner:** ChatBridge, LedgerLite
- **Least complete vendor:** ChatBridge

## How these numbers were checked

The expected import counts and scores above were reproduced with a separate throwaway script that applies the rules in this file to the two CSVs. Your own implementation in issues 10 and 15 should reproduce the same figures, which makes these files a ready-made test for both.

## Expected result of confirming the import (issues 10 and 11)

Load the vendors first (`python -m app.seed`), then import `apps.csv`.

| Measure | Expected |
|---|---|
| Applications created | 16 |
| Linked to a vendor | 11 |
| Left unassigned | 5 (Mystery PDF Tool, Quick Notes, Survey Maker, Calendar Sync Pro, and the formula row) |
| Matched by `subdomain` | 1 (ClinicNotes Reports, from `app.clinicnotes.example`) |
| Matched by `exact_domain` | 10 |

| Vendor | Applications linked |
|---|---|
| PayTrack | PayTrack Payroll, PayTrack Mobile |
| ClinicNotes | ClinicNotes Web, ClinicNotes Reports |
| QuickSign | QuickSign |
| ChatBridge | ChatBridge Desktop |
| Brightlearn LMS | Brightlearn LMS |
| MailBlast | MailBlast |
| DesignHub | DesignHub, DesignHub Plugin |
| LedgerLite | LedgerLite |

The import record shows 23 rows read, 16 new, 0 updated, 11 matched, 5 unassigned, 6 rejected and 1 duplicate. Importing the same file again gives 0 new and 16 updated, and the total stays at 16 applications.
