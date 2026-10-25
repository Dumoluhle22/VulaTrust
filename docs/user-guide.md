# User guide

VulaTrust helps you keep track of the outside services your business uses, what personal information they may handle, and which records need attention first.

> **Screenshots to add** (take these yourself and place them in `docs/screenshots/`):
> 1. The dashboard after importing the sample data
> 2. The CSV preview showing matched and unassigned rows
> 3. A vendor page showing its score and factors
> 4. The unassigned applications page
> 5. The vendor form with an error message

## Words used

| Word | Meaning |
|---|---|
| **Vendor** | A company that supplies you with a service |
| **Application** | A specific app or integration, such as a tool someone connected to a company account |
| **Operator agreement** | A written contract with a service that processes personal information for you. POPIA requires one. |
| **Unassigned** | An application that is not linked to a vendor yet |
| **Unknown** | You do not know the answer. The app never treats unknown as safe. |

## 1. Add a vendor

1. Choose **Vendors**, then **Add vendor**.
2. Enter the name. Everything else is optional, but the more you fill in, the better the score.
3. Enter the vendor's **domain** (for example `paytrack.example`). It is used to match imported applications. Pasting a web address is fine: it is cleaned automatically.
4. For each safeguard, choose Yes, No or **Unknown**. Choose Unknown if you are not sure.
5. If the operator agreement is **Signed**, enter the date it was signed. Leave the date blank for any other status.
6. Enter when the vendor was last reviewed and when the next review is due.
7. Choose **Save**.

## 2. Bring in a list of applications

1. Choose **Import**. Download the template if you need one.
2. Save your list as a **CSV UTF-8** file with these columns: `app_name`, `vendor_domain`, `source`, `user_count`, `scopes`, `privileged`. In Excel: Save As, then CSV UTF-8.
3. Choose your file and **Check file**. **Nothing is saved yet.**
4. Read the result:
   - **Rejected rows** are listed with their line number and every problem. Fix them in your file and check it again.
   - **Matched to a vendor** rows have a domain that one of your vendors uses.
   - **Left unassigned** rows could not be matched. The reason is shown.
   - **Warnings** tell you about changes made for safety, such as an apostrophe added to text starting with `=`.
5. Choose **Confirm import** to save. You land on a page for that import.

Importing the same file again updates the same applications. It does not create copies, and it never changes a link you made by hand.

## 3. Deal with unassigned applications

Open **Unassigned applications** from the dashboard. For each one:

- **Assign vendor** then **Link to an existing vendor**, or
- **Create a new vendor**, which starts with the application's name and domain and links the two when you save.

After adding vendors, use **Match again using current vendors** to link everything whose domain now matches.

## 4. Read a vendor's score

Open a vendor from the list. The **Risk score** section shows:

- The score out of 100 and its level: **High** (70 or more), **Medium** (40 to 69) or **Low** (below 40).
- **Completeness**: how many of seven fields are known, and which are missing.
- Each **factor** that added points, with the points, the reason, and whether it is **confirmed** or **unverified**.

**Unverified** means the information is missing, so the factor counts for half its points. Filling in the missing information removes the doubt. The score helps you decide where to look first. It is **not proof** that a vendor is secure or insecure, and a recorded agreement is not necessarily legally adequate.

To lower a score, deal with its factors: sign an operator agreement, assign an owner, do the review, or check where the data is hosted.

## 5. Use the dashboard

The dashboard (the home page) shows:

- Totals, and how many vendors are High, Medium and Low. Click a level to see those vendors.
- **Highest scores**: where to look first.
- **No signed operator agreement**: vendors that handle, or may handle, personal information.
- **Reviews overdue or never done.**
- **Vendors with no owner.**
- **Least complete records**: vendors with the most unknowns, who may be hiding problems.
- **Unassigned applications.**

## Keeping it up to date

A few minutes a month is enough: import the latest application list, deal with the unassigned ones, and work through the dashboard lists from the top.

## Good to know

- There is no login, so keep the app on your own computer.
- Scores use today's date, so a vendor can become overdue as time passes.
- The app records what you tell it. It does not check a vendor's security.
