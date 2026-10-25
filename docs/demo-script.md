# Demo script (about 10 minutes)

Uses only the synthetic sample data. Every figure below was checked against the real app.

## Before you start

1. Stop the server, delete `vulatrust.db`, then run `python -m app.seed`.
2. Start the app: `python -m uvicorn app.main:app --reload`, and open http://127.0.0.1:8000.
3. Have `sample_data/apps.csv` ready to upload.

The figures assume you demo before February 2027. After that, Brightlearn LMS's next review date has passed and its numbers change.

## 1. The problem, then an empty-ish start (1 min)

Say: small businesses use many outside services, staff connect apps nobody lists, and POPIA expects a written operator agreement where personal information is processed. Nobody has one clear picture.

Show the dashboard: **8 vendors, 0 applications.** Two vendors already score High (ClinicNotes and MailBlast, 70 each).

Point out: with no applications recorded, the app cannot check privileged access, so it counts half the points as **unverified**. Missing information is never treated as safe.

## 2. Import a file (2 min)

Open **Import**, choose `apps.csv`, **Check file**. Nothing is saved yet. Show:

- **23 rows read, 16 ready, 1 duplicate skipped, 6 rejected.**
- **11 matched to a vendor, 5 left unassigned, 16 new.**
- The rejected table, with its line numbers: line 19 (user count "abc"), 20 (negative), 21 (source "dropbox"), 22 (privileged "maybe"), 23 (over-long text), 24 (no name).
- The warning on line 17: a name starting with `=` got an apostrophe, so a spreadsheet cannot run it as a formula.
- In the preview, `ClinicNotes Reports` matched by **Subdomain** and the unassigned rows each say why.

Choose **Confirm import**. You land on the import page: 16 applications.

## 3. The dashboard (1 min)

Go to the dashboard. Show:

| Item | Figure |
|---|---|
| Vendors / applications / unassigned | 8 / 16 / 5 |
| High / Medium / Low | 1 / 4 / 3 |
| Highest scores | ClinicNotes 85, ChatBridge 68, MailBlast 60, LedgerLite 50, Brightlearn LMS 40 |
| No signed operator agreement | ClinicNotes, ChatBridge, MailBlast, Brightlearn LMS |
| Reviews overdue or never done | ChatBridge (never), LedgerLite, MailBlast, ClinicNotes |
| No owner | ChatBridge, LedgerLite |
| Least complete | ChatBridge (0 of 7), LedgerLite (6 of 7) |

## 4. Why is ClinicNotes 85? Fix it. (2 min)

Open **ClinicNotes**. The score is **85, High**. Read the factor table: personal information without a signed agreement 35, broad access 20, review overdue 15, hosted outside South Africa 10, many users 5. All are **confirmed**.

Choose **Edit vendor**:

1. Set the operator agreement to **Signed** and enter a past date. Save. The score drops to **50, Medium**.
2. Edit again: last reviewed a past date, next review due a future date. Save. The score drops to **35, Low**.

Mention that the form refuses a signed status with no date, and a future signing date.

## 5. Unknown is not safe (1 min)

Open **ChatBridge**: **68, Medium, 0 of 7 fields known.** Several factors are tagged **unverified** and count for half. A vendor you know nothing about does not look low risk.

## 6. Unassigned applications (2 min)

Open **Unassigned applications** from the dashboard: five applications (Calendar Sync Pro, the `=1+1` one, Mystery PDF Tool, Quick Notes, Survey Maker).

For **Quick Notes**: **Assign vendor**, then **Create a new vendor**. The name and domain are copied from the application. Save. The vendor page says the application is now linked.

- The new vendor scores **58, Medium, with only 1 of 7 fields known.** It appears in "Least complete records".
- Unassigned drops to **4**. Vendors are now 9.

## 7. Importing again (1 min)

Import `apps.csv` again. The preview says **0 new, 16 will be updated.** Confirm. Open **Import history**: two imports. In **Applications**, Quick Notes is still "Linked manually". An import never overrides a link a person made.

## 8. Close (30 seconds)

- **333 automated tests, 98% coverage**, including injection, script injection and CSRF checks.
- Honest limits: no login (keep it local), no real Google or Microsoft connection yet, weights not validated against real incidents, and it records agreements without judging whether they are adequate.

## Questions you may be asked

| Question | Short answer |
|---|---|
| Why not a spreadsheet? | A spreadsheet is the real competitor. This fills the register from an import, finds applications nobody listed, and calculates and explains priorities and overdue reviews instead of relying on memory. |
| Does it make a business POPIA compliant? | No. It helps organise the records POPIA expects, such as operator agreements. It does not judge whether they are adequate. |
| Why do unknowns count half? | So missing information is never treated as safe, but one gap does not look as bad as a confirmed problem. |
| Where do the weights come from? | They are a reasoned starting point, explained in `docs/scoring.md`, and not validated against real incidents. |
| How does it differ from Aperio and open-SSPM? | They find and govern applications. Neither has a vendor record, agreement tracking or a vendor-level score. See `docs/related-work.md`. |
| What would you build next? | Login and roles, an audit log, direct Google Workspace and Microsoft 365 import, CSV export, review reminders. |
