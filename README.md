# VulaTrust

## Open-Source SaaS Discovery & Vendor Assurance for South African SMEs

**Know which third-party apps your business uses, what information they may access, and which vendor records need attention.**

VulaTrust is an open-source cybersecurity tool for small and medium-sized South African businesses. It connects a list of discovered SaaS applications to a vendor register, tracks POPIA-related records, and ranks vendors with a score that explains itself, so a business without a security team can see where to look first.

> **Project status:** working prototype. The core features below are built and tested. User interviews and the usability test are still to be completed (see [Limitations](#14-limitations)). The tool has no login, so run it on your own computer only.

---

## Table of contents

1. [Central research question](#1-central-research-question)
2. [The problem](#2-the-problem)
3. [Who is affected](#3-who-is-affected)
4. [Targeted industries](#4-targeted-industries)
5. [Existing work and the gap](#5-existing-work-and-the-gap)
6. [What VulaTrust does](#6-what-vulatrust-does)
7. [Quick start](#7-quick-start)
8. [How the score works](#8-how-the-score-works)
9. [Scope](#9-scope)
10. [Technology](#10-technology)
11. [Project layout and documentation](#11-project-layout-and-documentation)
12. [Security](#12-security)
13. [Testing and evaluation](#13-testing-and-evaluation)
14. [Limitations](#14-limitations)
15. [Contributing and licence](#15-contributing-and-licence)
16. [Disclaimer](#16-disclaimer)
17. [References](#17-references)

---

## 1. Central research question

**How do businesses understand and manage the security risks created by external vendors and SaaS applications connected to their business?**

Two focus areas:

- **Vendor risk:** knowing who your suppliers are, what data they handle, and whether the right safeguards and agreements exist.
- **SaaS shadow IT:** finding applications that staff connected to company accounts without anyone formally approving them.

The project's working question is narrower: **can a focused workflow that connects discovered SaaS applications to vendor-assurance records make this information easier to maintain and act on for small South African businesses?** This is a hypothesis to validate, not a settled fact.

---

## 2. The problem

Small businesses rely on third-party services for accounting, payroll, email, file sharing, customer management and daily operations. Employees connect more of them to company accounts, for example by choosing "Sign in with Google". Information about suppliers, data handling, agreements and review dates ends up scattered across spreadsheets, emails and documents.

That causes three practical problems:

- **Incomplete visibility:** nobody has a full list of the applications connected to company accounts.
- **Disconnected records:** application lists and vendor-assurance information are kept separately, if at all.
- **Unclear priorities:** owners cannot easily see missing records, overdue reviews, or what warrants a closer look.

### Why POPIA makes this matter

South Africa's Protection of Personal Information Act (POPIA) puts responsibility on the business that decides how personal information is processed. Depending on the processing relationship:

- Section 21 requires a **written contract** with an operator (an outside party processing personal information on your behalf), requiring it to maintain the security measures in section 19.
- The business generally **remains responsible** for the security of that information even when an operator handles it.
- The Information Regulator has enforced this. In its enforcement notice against Dis-Chem, it found the company had not concluded a written contract with its operator.

VulaTrust helps organise the relevant records and follow-up actions. **It is not a legal compliance tool.**

---

## 3. Who is affected

| Group | How they are affected |
| --- | --- |
| **Business owners and directors** | Accountable under POPIA. In many companies the CEO is automatically the information officer, so they carry the risk without necessarily having a security background. |
| **Office managers and IT contractors** | Often the people who end up tracking vendors, with little time and no specialist tools. |
| **Employees** | Connect applications to company accounts to get work done, often without knowing what access they grant. |
| **Customers, patients and learners (data subjects)** | Their personal information is exposed if a vendor is breached or misconfigured. |
| **Vendors and suppliers** | Are asked for agreements and security evidence, usually ad hoc. |
| **Regulators** | The Information Regulator expects documented operator agreements and security measures. |

---

## 4. Targeted industries

The focus is South African SMEs that use third-party software to handle business or personal information but have limited dedicated cybersecurity resources. These segments are **assumptions, not confirmed users**:

- **Healthcare practices and clinics:** patient records in practice-management and billing software.
- **Accounting, legal and advisory firms:** client financial data across many cloud tools.
- **Insurance and financial-services brokers:** personal and financial information shared with providers.
- **Retail and e-commerce:** customer data in payment, marketing and delivery platforms.
- **Education and training providers:** learner records in learning-management systems.
- **Property and recruitment agencies:** ID documents and employment data shared with several platforms.
- **NGOs and non-profits:** donor and beneficiary data in free or low-cost tools.

The tool itself is industry-neutral. The segments mainly decide which examples and interview participants are used.

---

## 5. Existing work and the gap

VulaTrust does **not** claim that vendor-risk management is missing from the open-source world. Existing projects cover parts of the problem.

| Project | Focus | Verified how |
| --- | --- | --- |
| [Aperio](https://github.com/writer/aperio) | SaaS security posture, OAuth app discovery, findings sent to a SIEM | README, database schema and a search of the full source |
| [open-SSPM](https://github.com/open-sspm/open-sspm) | "Who has access to what": identities, permissions, discovered apps, review workflow | README, database schema and a search of the full source |
| [CISO Assistant Community Edition](https://github.com/intuitem/ciso-assistant-community) | Broad governance, risk and compliance, including third-party risk and contracts | README and feature list only |

Searching Aperio's and open-SSPM's schemas and code for vendor-assurance terms (SOC 2, ISO 27001, questionnaires, data processing agreements, data residency, POPIA, "vendor risk") found nothing relevant. Details are in [`docs/related-work.md`](docs/related-work.md).

| Capability | Aperio | open-SSPM | VulaTrust |
| --- | --- | --- | --- |
| Discovers third-party apps | Yes (OAuth) | Yes (SSO and OAuth) | Via CSV import |
| App-level risk score | Yes | Yes | Per vendor, using app data |
| First-class vendor record | No | Text label only | Yes |
| Several apps grouped under one vendor | No | No | Yes |
| Operator-agreement tracking (POPIA s21) | No | No | Yes |
| Hosting location per vendor | No | No | Yes |
| Vendor-level risk score | No | No | Yes |
| Review-due tracking per vendor | No | App review date only | Yes |
| Built for non-security staff | No (SIEM-centred) | No (identity-centred) | Intended, not yet tested with users |

**Honest positioning.** Both SSPM tools find and govern applications but never answer "which vendor is this, and do we have the right agreement?". General GRC tools such as CISO Assistant cover vendors but are built for dedicated security teams. VulaTrust tries to join discovery to a simple vendor register for a small business under POPIA. Whether that is worth having is what the research and usability testing are meant to show.

**Versus a spreadsheet.** A spreadsheet is the realistic alternative. VulaTrust's possible advantages are that an import fills the register (so applications nobody remembered to list appear), and that scores, overdue reviews and priorities are calculated and explained instead of relying on memory.

---

## 6. What VulaTrust does

- **Vendor register:** name, domain, owner, whether it handles personal information, data handled, hosting location, operator-agreement status and date, certifications, review dates and notes.
- **Application register:** applications linked to vendors, with source, number of users, access description and a privileged-access flag. Applications can be unassigned.
- **CSV import with a safe preview:** a file is checked first and nothing is saved until you confirm. Every rejected row is listed with its line number and every problem. Imports are all-or-nothing and re-importing updates rather than duplicates.
- **Vendor matching by domain:** exact and subdomain matches, never guessed, with the method recorded. Links made by hand are never overridden.
- **Unassigned applications:** link to an existing vendor, create a vendor from the application, or match again after adding vendors.
- **Explainable risk score:** see [section 8](#8-how-the-score-works).
- **Dashboard:** counts by risk level, highest scores, vendors with no signed operator agreement, overdue reviews, vendors with no owner, least complete records, and unassigned applications.
- **Safety and honesty:** unknown is never treated as safe, and every score lists its reasons.

---

## 7. Quick start

Needs Python 3.10 or newer. Full instructions, including Windows and troubleshooting, are in [`docs/setup.md`](docs/setup.md).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest                   # run the tests
python -m app.seed                 # load 8 synthetic sample vendors
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>, then go to **Import** and upload `sample_data/apps.csv`. The expected results are listed in [`sample_data/README.md`](sample_data/README.md), and a 10-minute walkthrough is in [`docs/demo-script.md`](docs/demo-script.md).

---

## 8. How the score works

Each vendor gets a score from 0 to 100 and a level: **High** (70 or more), **Medium** (40 to 69) or **Low** (below 40).

| Factor | Points |
| --- | --- |
| Handles personal information and has no signed operator agreement | 35 |
| Has an application with broad (privileged) access | 20 |
| No owner assigned | 15 |
| Review overdue, or never reviewed | 15 |
| Hosted outside South Africa | 10 |
| Five or more users connected | 5 |

- **Unknown is never treated as safe.** An unknown input adds half of that factor's points and is labelled **unverified**.
- Each score is shown with its **completeness** (how many of seven fields are known) and the reason for every factor.
- The score decides where to look first. It is **not proof** that a vendor is secure or insecure.

The weights are a reasoned starting point and have not been validated against real incidents. Full details and the reasoning are in [`docs/scoring.md`](docs/scoring.md).

---

## 9. Scope

### Built

- Vendor and application registers with validation and safe defaults
- CSV check, preview, confirm, history, matching and re-import
- Operator-agreement and review-date rules
- Explainable vendor score and dashboard
- Security protections (see section 12)
- Synthetic sample data with documented expected results, and automated tests

### Not built (possible future work)

- Login and roles, and an audit log
- Direct import from Google Workspace or Microsoft 365
- CSV or PDF export, review reminders, follow-up actions, match-confidence indicators

### Out of scope

- Real-time monitoring or SIEM functions
- Scanning vendors from outside, or breach monitoring
- Automated legal interpretation of contracts
- Claims of POPIA compliance
- Multi-organisation hosting
- Automatic revocation of application permissions

---

## 10. Technology

| Component | Technology |
| --- | --- |
| Language | Python 3.10+ |
| Web framework | FastAPI with Uvicorn |
| Database | SQLite through SQLAlchemy |
| Validation | Pydantic |
| Pages | Server-rendered Jinja2 templates. No JavaScript. |
| Tests | pytest, with pytest-cov for coverage |
| Automation | A GitHub Actions workflow runs the tests (not yet run on GitHub) |

---

## 11. Project layout and documentation

```text
app/            application code (see docs/data-model.md for the module map)
tests/          automated tests
sample_data/    synthetic vendors and applications, with expected results
docs/           documentation
```

| Document | What it covers |
| --- | --- |
| [`docs/setup.md`](docs/setup.md) | Install, run, reset, troubleshoot |
| [`docs/user-guide.md`](docs/user-guide.md) | How to use each screen |
| [`docs/data-model.md`](docs/data-model.md) | Tables, fields and the code layout |
| [`docs/scoring.md`](docs/scoring.md) | The score, unknown handling, reasoning and limits |
| [`docs/security-notes.md`](docs/security-notes.md) | Protections, tests and known gaps |
| [`docs/testing.md`](docs/testing.md) | Test inventory, coverage and what is not covered |
| [`docs/related-work.md`](docs/related-work.md) | What was checked about similar projects |
| [`docs/demo-script.md`](docs/demo-script.md) | A 10-minute demonstration |
| [`docs/report-outline.md`](docs/report-outline.md) | Report structure and the evaluation table |
| [`docs/interview-guide.md`](docs/interview-guide.md), [`docs/usability-test.md`](docs/usability-test.md) | Guides for the user research |

---

## 12. Security

VulaTrust stores business records, so it protects them where it can. Highlights:

- Database access through parameterised queries, and all page text escaped. Pages contain no scripts, and a strict Content-Security-Policy is set.
- **CSRF protection** on every form (a random token matched to a `SameSite=Strict` cookie), with a test that fails if a new form lacks it.
- Uploads limited to `.csv`, 1 MB, 5,000 rows and UTF-8 text. Files are never saved or executed, and spreadsheet formula characters are neutralised.
- The generated API docs and debug mode are off, and responses are not cached.

**The largest gap: there is no login.** Run it only on your own computer and never expose it to a network. Other known gaps (no HTTPS, no rate limiting, no audit log, unpinned dependencies) are listed in [`docs/security-notes.md`](docs/security-notes.md).

---

## 13. Testing and evaluation

**333 automated tests pass, with 98% line coverage of `app/`.** Details are in [`docs/testing.md`](docs/testing.md).

| Criterion | Result |
| --- | --- |
| A CSV of about 20 synthetic applications imports without errors | Met. 23 rows read, 16 imported, 1 duplicate and 6 invalid rows reported |
| At least 90% of applications that belong to a registered vendor match it by domain | Met, 11 of 11, on the synthetic sample |
| Unmatched applications stay visible | Met |
| Scores are reproducible and every factor is visible | Met |
| Personal information with no signed agreement scores at least 35 | Met |
| Unknown information is flagged and not treated as safe | Met |
| Adding an agreement, owner or review lowers the score as expected | Met |
| Missing agreements and overdue reviews are identified | Met |
| Input validation and database tests pass | Met |
| People without a security background complete the key tasks | **Not yet measured**, see [`docs/usability-test.md`](docs/usability-test.md) |

These results come from a small synthetic data set. Real files will be messier.

---

## 14. Limitations

- The need for this workflow has **not yet been validated** through user interviews or a usability test.
- Existing tools may already satisfy some of the proposed requirements. CISO Assistant was reviewed at feature-list level only, and commercial vendor-risk platforms were not researched.
- The target industries and users are assumptions.
- The scoring weights and thresholds are provisional and not validated against real incidents.
- Imported application lists may be incomplete or out of date, and matching a domain to a vendor can be ambiguous, which is why unclear cases stay unassigned.
- Two applications with the same name, domain and source are treated as one.
- Only CSV import exists. There is no direct Google Workspace or Microsoft 365 connection.
- Recording an agreement does not show it is legally adequate, and the tool does not establish POPIA compliance.
- A vendor reviewed once with no next review date is not counted as overdue.
- The app is single-user with no login (see section 12).
- Aperio and open-SSPM were reviewed from snapshots and may have changed.

---

## 15. Contributing and licence

Contributions are welcome: see [`CONTRIBUTING.md`](CONTRIBUTING.md). Use synthetic data only. Released under the MIT licence (see `LICENSE`).

---

## 16. Disclaimer

VulaTrust is a research and software-development project. It is not legal advice, a compliance certification, or a guarantee that a vendor or application is secure.

---

## 17. References

- Aperio: <https://github.com/writer/aperio>
- open-SSPM: <https://github.com/open-sspm/open-sspm>
- CISO Assistant Community Edition: <https://github.com/intuitem/ciso-assistant-community>
- Information Regulator, Dis-Chem enforcement notice: <https://inforegulator.org.za/wp-content/uploads/2020/07/DIS-CHEM-ENFORCEMENT-NOTICE.pdf>
- Fasken, "Beware of the Operator Contract" (POPIA s21): <https://fasken.com/en/knowledge/2023/09/beware-of-the-operator-contract-a-necessity-for-popia-compliance>
- CMS, "Data breaches: prevention is better than cure" (POPIA s19 and operators): <https://cms.law/en/zaf/publication/data-breaches-prevention-is-better-than-cure>
- Michalsons, "Does someone else process your personal information?": <https://www.michalsons.com/focus-areas/privacy-and-data-protection/does-someone-else-process-your-personal-information>
- Information Regulator of South Africa: <https://inforegulator.org.za/>
- Protection of Personal Information Act 4 of 2013: <https://www.gov.za/documents/protection-personal-information-act>
