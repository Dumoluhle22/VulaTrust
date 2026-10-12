# VulaTrust
### Open-Source SaaS Discovery & Vendor Assurance for South African SMEs

**Know which third-party apps your business uses, what information they may access, and which vendor records need attention.**

VulaTrust is a proposed open-source cybersecurity tool that helps small and medium-sized South African businesses connect third-party SaaS application inventories with vendor-assurance records.

The project explores whether a lightweight, explainable workflow can help businesses identify unassigned applications, track POPIA-related records, and prioritise vendor reviews without a dedicated security team.

> **Project status:** Research and development. The features below describe the intended project, and not all of them are implemented yet.

---

## Table of contents

1. [Central research question](#1-central-research-question)
2. [The problem](#2-the-problem)
3. [Who is affected](#3-who-is-affected)
4. [Targeted industries](#4-targeted-industries)
5. [Existing work and the gap](#5-existing-work-and-the-gap)
6. [Proposed solution](#6-proposed-solution)
7. [Scope](#7-scope)
8. [Data model](#8-data-model-starting-point)
9. [Risk scoring](#9-risk-scoring-provisional)
10. [Security and privacy principles](#10-security-and-privacy-principles)
11. [Technology stack](#11-technology-stack)
12. [Development roadmap](#12-development-roadmap)
13. [Evaluation criteria](#13-evaluation-criteria)
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

Small businesses increasingly rely on third-party services for accounting, payroll, email, file sharing, customer management and daily operations.

Over time, employees may authorise additional applications through company accounts, for example by choosing "Sign in with Google" or approving an app's access request. Meanwhile, information about suppliers, data handling, operator agreements and review dates is scattered across spreadsheets, emails and documents.

This creates three practical challenges:

- **Incomplete visibility:** the business may not have a consolidated inventory of the third-party applications connected to its accounts.
- **Disconnected records:** application inventories and vendor-assurance information are maintained separately, if at all.
- **Unclear priorities:** business owners struggle to see missing records, overdue reviews and applications that warrant a closer look.

### Why POPIA makes this matter

South Africa's Protection of Personal Information Act (POPIA) puts responsibility on the business that decides how personal information is processed. Depending on the processing relationship:

- Section 21 requires a **written contract** with an operator (an outside party processing personal information on the business's behalf), requiring the operator to maintain the security measures in section 19.
- The business generally **remains responsible** for the security of that information even when an operator handles it.
- The Information Regulator has enforced this. In its enforcement notice against Dis-Chem, it found that the company had not concluded a written contract with its operator.

VulaTrust aims to help organise the relevant records and follow-up actions. **It is not a legal compliance certification tool.**

---

## 3. Who is affected

| Group | How they are affected |
|---|---|
| **Business owners and directors** | Accountable under POPIA. In many companies the CEO is automatically the information officer, so they carry the risk without necessarily having a security background. |
| **Office managers and IT contractors** | Often the people who end up tracking vendors, with little time and no specialist tools. |
| **Employees** | Connect applications to company accounts to get work done, often without knowing what access they are granting. |
| **Customers, patients and learners (data subjects)** | Their personal information is exposed if a vendor is breached or misconfigured. |
| **Vendors and suppliers** | Are asked for agreements and security evidence, usually ad hoc. |
| **Regulators** | The Information Regulator expects documented operator agreements and security measures. |

---

## 4. Targeted industries

The initial focus is South African SMEs that use third-party software to handle business or personal information but have limited dedicated cybersecurity resources.

Proposed starting segments (these are assumptions, not confirmed users, and their needs must be investigated):

- **Healthcare practices and clinics:** patient records in practice-management and billing software.
- **Accounting, legal and advisory firms:** client financial data across many cloud tools.
- **Insurance and financial-services brokers:** personal and financial information shared with providers.
- **Retail and e-commerce:** customer data in payment, marketing and delivery platforms.
- **Education and training providers:** learner records in learning-management and administration systems.
- **Property and recruitment agencies:** ID documents, contact and employment data shared with several platforms.
- **NGOs and non-profits:** donor and beneficiary data in free or low-cost tools.

The prototype itself is industry-neutral. The segments mainly decide which sample data, examples and interview participants are used.

---

## 5. Existing work and the gap

VulaTrust does **not** claim that vendor-risk management is missing from the open-source ecosystem. Existing projects already address parts of the problem.

### Projects reviewed

Aperio and open-SSPM were reviewed by reading their READMEs, database schemas and source code (main-branch snapshots, October 2026). CISO Assistant was reviewed at README and feature-list level only.

**[Aperio](https://github.com/writer/aperio)** (SaaS security posture, discovery and findings)
- Detects SaaS posture risks and inventories OAuth-authorised apps, then streams findings to a SIEM.
- Models apps as a security asset with technical and business owners, criticality, a sensitive-data flag and a risk score, plus a risk-exception workflow (rationale, controls, expiry, approver).
- Has no vendor entity. The only "vendor" fields in its code describe SIEM products.

**[open-SSPM](https://github.com/open-sspm/open-sspm)** (SaaS visibility, identity and access governance)
- A "who has access to what" service that syncs identities and permissions from an identity provider and connected apps.
- Builds a discovered-app inventory, a review workflow (sanctioned, tolerated, replace, owner, follow-up date, ticket reference) and an app-level risk score from 0 to 100.
- `vendor_name` is a text label on the app. The code uses the vendor name a connector reports, or derives a label from the app's domain.

**[CISO Assistant Community Edition](https://github.com/intuitem/ciso-assistant-community)** (broader GRC)
- A general open-source governance, risk and compliance platform whose features include third-party risk management, contracts management and evidence management.
- Built for security and compliance teams. Its third-party module has not yet been examined in depth.

### Gap

Searching the full source of Aperio and open-SSPM for vendor-assurance terms (SOC 2, ISO 27001, questionnaire, data processing agreement, data residency, POPIA, GDPR, third-party or vendor risk) found nothing relevant in either.

| Capability | Aperio | open-SSPM | VulaTrust (planned) |
|---|---|---|---|
| Discovers third-party apps | Yes (OAuth) | Yes (SSO and OAuth) | Via CSV import |
| App-level risk score | Yes | Yes | Yes |
| First-class vendor record | No | Text label only | Yes |
| Several apps grouped under one vendor | No | No | Yes |
| Operator-agreement tracking (POPIA s21) | No | No | Yes |
| Hosting location per vendor | No | No | Yes |
| Vendor-level risk score | No | No | Yes |
| Review-due tracking per vendor | No | App review date only | Yes |
| Aimed at non-security staff | No (SIEM-centred) | No (identity-centred) | Yes |

### Why not a spreadsheet?

A spreadsheet is a serious alternative and is what most small businesses use today. VulaTrust's value depends on whether these provide enough benefit to justify a dedicated tool:

- imports that fill the register instead of typing vendors in by hand,
- vendor matching that surfaces apps nobody remembered to list,
- transparent, calculated prioritisation,
- review dates that are tracked rather than remembered.

---

## 6. Proposed solution

VulaTrust connects application discovery with a practical vendor register. Instead of treating each discovered application as an isolated entry, it lets applications be matched to vendors and associated with the data handled, hosting location, operator-agreement status, assurance evidence and review dates.

The intended workflow:

1. **Import:** bring in a list of third-party applications from CSV.
2. **Match:** link applications to existing vendor records using identifiers such as domains.
3. **Review:** flag applications that cannot confidently be matched to a vendor.
4. **Record:** track vendor information and operator-agreement status.
5. **Prioritise:** calculate an explainable provisional score and highlight outstanding actions.

Design principle: **minimal required data entry.** The person maintaining the register may spend only a few minutes a month, so most fields are optional and imports should do most of the filling.

Automatic discovery through Google Workspace or Microsoft 365 is a possible extension, subject to feasibility testing.

---

## 7. Scope

### MVP (planned)

**Vendor inventory**
- Create, edit and list vendor records with a business owner.
- Record categories of information handled, hosting location and certifications noted.
- Track operator-agreement status (none, requested, signed) and its date.

**Application inventory**
- Import application records from CSV with validation and unmatched-record handling.
- Link applications to vendors; record discovery source, user counts and access scopes.
- Keep unassigned applications visible in a review queue.
- Keep an import record for traceability.

**Review tracking**
- Last-reviewed and next-review-due dates, with an overdue flag.
- Flag missing or unverified information.

**Explainable prioritisation**
- Provisional vendor-level score with documented factors and weights.
- Show which factors contributed, and separate known risks from missing information.

**Dashboard**
- Vendors requiring attention, missing operator agreements, overdue reviews, unassigned applications, and vendors with incomplete information.

**Supporting material**
- Synthetic sample data, automated tests and setup documentation.

### Stretch (only if time allows)

- Follow-up action tracking for issues needing attention.
- Audit log of important record changes.
- Login and roles, if the app is demonstrated as a deployed service.
- Direct import from Google Workspace or Microsoft 365.
- Matching confidence indicators.
- CSV or PDF export, and review reminders.
- Additional assurance-evidence workflows.

### Out of scope

- Real-time security monitoring or SIEM functionality.
- External vendor vulnerability scanning or breach monitoring.
- Automated legal interpretation of contracts.
- Automatic claims of POPIA compliance.
- Enterprise-scale multi-organisation hosting.
- Automatic revocation of application permissions.

---

## 8. Data model (starting point)

Names and types may change as the design is tested.

**Known, unknown, or not applicable.** Fields that describe a vendor's safeguards should allow **yes, no or unknown**, never a silent default. Unknown must stay visible and must not be treated as evidence of safety.

### vendors

| Field | Notes |
|---|---|
| id, name, primary_domain | The domain helps match discovered applications |
| owner | Person responsible for the relationship |
| handles_personal_info | yes / no / unknown |
| data_types | Free text or tags, for example customer contact details, health, payroll |
| hosting_location | South Africa / outside South Africa / unknown |
| operator_agreement_status | none / requested / signed / unknown |
| operator_agreement_date | Date signed, if any |
| certifications | Free text, for example SOC 2, ISO 27001 |
| last_reviewed, next_review_due | Dates |
| notes | Free text |

### applications

| Field | Notes |
|---|---|
| id, name | Discovered or manually added |
| vendor_id | Nullable, so unmatched applications show as unassigned |
| source | manual / csv / google / microsoft |
| discovered_at | Date of import |
| user_count | Number of people who authorised or use it |
| scopes | Text summary of the access granted |
| privileged | yes / no / unknown (broad access such as full mailbox or drive) |

### import_batches

id, source, imported_at, row_count and filename, so imports can be traced.

### Sample CSV

```csv
app_name,vendor_domain,source,user_count,scopes,privileged
Example Scheduler,examplescheduler.com,google,12,"calendar read/write",no
Example File Share,examplefiles.io,google,4,"full drive access",yes
```

Use synthetic data. If you test with a real Google account's third-party access list, anonymise it before anything enters the repository.

---

## 9. Risk scoring (provisional)

The score is deliberately simple so a business owner can see why a vendor is flagged. The idea of a transparent points formula is borrowed from open-SSPM's approach, but this version works at vendor level and adds POPIA-related factors. **Weights and thresholds are provisional. Tune them during testing and justify the final choices.**

| Factor | Points |
|---|---|
| Handles personal information and no signed operator agreement | 35 |
| Has an application with a privileged access scope | 20 |
| No owner assigned | 15 |
| Review overdue or never reviewed | 15 |
| Hosted outside South Africa | 10 |
| Five or more users connected to it | 5 |

- The total is capped at 100.
- Suggested levels: 70 or more is high, 40 to 69 is medium, below 40 is low.
- **Unknown inputs** add half of a factor's points and are labelled "unverified", so missing information is never scored as safe.
- Each score is shown with a **completeness figure** (for example, "score 55, 4 of 7 fields known") and the list of contributing factors.

The score prioritises attention. It is not proof that a vendor is secure or insecure.

---

## 10. Security and privacy principles

VulaTrust is itself a security-related application, so its design must account for the information it stores.

The project aims to incorporate:

- Input validation and safe database access (parameterised queries through the ORM).
- Secure handling of imported files (size and type limits, no execution of content).
- Minimal collection of personal and sensitive information.
- Clear separation between confirmed information, inferred matches and unknowns.
- Automated tests for important security and data-integrity requirements.
- Authentication, authorisation and an audit log if a deployed version is demonstrated (see stretch scope).

Development and demonstrations should use synthetic data wherever possible. Real application credentials, access tokens and unnecessary personal information must not be committed to the repository.

---

## 11. Technology stack

| Component | Technology | Priority |
|---|---|---|
| Language | Python | Core |
| Web framework | FastAPI | Core |
| Database | SQLite for local development | Core |
| Database access | SQLAlchemy | Core |
| Data validation | Pydantic | Core |
| Interface | Server-rendered HTML with Jinja2 | Core |
| Testing | pytest | Core |
| Version control | Git and GitHub | Core |
| Interactivity | HTMX | Optional |
| Continuous integration | GitHub Actions | Optional |

The stack may change as the design is tested. The priority is to keep the first version understandable, testable and practical to run locally. If time runs short, drop the optional items first.

---

## 12. Development roadmap

Each phase should leave something that runs.

### Phase 1: Research and validation
- Finish the feature and workflow comparison of existing projects.
- Examine CISO Assistant's third-party-risk module in more depth.
- Interview a small number of potential users about how they track vendors today.
- Refine the research question and MVP scope.

### Phase 2: Data model and inventory
- Create the database and the vendor and application tables.
- Build add, edit and list screens for vendors and applications.
- Add the "unassigned applications" view.

### Phase 3: Import and matching
- Implement CSV validation and import with an import record.
- Match applications to vendors by domain.
- Handle duplicates and unmatched applications.

### Phase 4: Assurance and prioritisation
- Add operator-agreement and review fields and the overdue calculation.
- Implement scoring with unknown handling and the completeness figure.
- Test behaviour against synthetic scenarios.

### Phase 5: Dashboard
- Build counts by level and lists of missing agreements, overdue reviews, unassigned applications and incomplete vendors.

### Phase 6: Evaluation and documentation
- Run the automated tests and a small usability test.
- Document limitations, results and lessons learned.
- Publish the code and contribution guidance.

---

## 13. Evaluation criteria

The prototype will be evaluated against practical, testable outcomes. The targets below are starting points and may be adjusted.

- A valid CSV of about 20 synthetic applications imports without errors, and at least 90% are matched to the correct vendor by domain.
- Unmatched applications remain visible for review.
- Vendor and application relationships are represented consistently.
- Risk scores are reproducible, and their contributing factors are visible.
- A vendor that handles personal information with no signed agreement always scores at least 35.
- Unknown information is flagged and not treated as evidence of safety.
- Adding an agreement, an owner or a review changes the score and level in the expected direction.
- Missing agreement records and overdue reviews are identified correctly.
- Input validation and database operations pass their tests.
- Three people without a cybersecurity background complete the key tasks (add a vendor, import apps, find overdue reviews) in a usability test.

The project will report what testing demonstrates and will not assume that the tool improves security simply because it produces a score.

---

## 14. Limitations

- The need for this particular workflow has not yet been validated through user interviews.
- Existing tools may already satisfy some or all of the proposed requirements.
- CISO Assistant was reviewed at feature-list level only, and commercial vendor-risk platforms were not researched.
- The target industries and users are assumptions.
- The risk-scoring weights and thresholds are provisional and have not been validated against real incidents.
- Imported application inventories may be incomplete or out of date.
- Application-to-vendor matching may be ambiguous and require human confirmation.
- Recording an agreement does not establish that the agreement is legally adequate.
- The prototype will not independently establish POPIA compliance.
- Aperio and open-SSPM were reviewed from snapshots and may change.

---

## 15. Contributing and licence

VulaTrust is intended to be developed as an open-source learning and portfolio project.

Potential contributions:

- Bug reports and reproducible test cases.
- Improvements to CSV validation and application matching.
- Additional synthetic test scenarios.
- Documentation and usability improvements.
- Security-focused code review.

Released under the MIT licence. See the `LICENSE` file once the repository is established.

---

## 16. Disclaimer

VulaTrust is a research and software-development project. It is not legal advice, a compliance certification, or a guarantee that a vendor or application is secure.

---

## 17. References

- Aperio: https://github.com/writer/aperio
- open-SSPM: https://github.com/open-sspm/open-sspm
- CISO Assistant Community Edition: https://github.com/intuitem/ciso-assistant-community
- Information Regulator, Dis-Chem enforcement notice: https://inforegulator.org.za/wp-content/uploads/2020/07/DIS-CHEM-ENFORCEMENT-NOTICE.pdf
- Fasken, "Beware of the Operator Contract" (POPIA s21): https://fasken.com/en/knowledge/2023/09/beware-of-the-operator-contract-a-necessity-for-popia-compliance
- CMS, "Data breaches: prevention is better than cure" (POPIA s19 and operators): https://cms.law/en/zaf/publication/data-breaches-prevention-is-better-than-cure
- Michalsons, "Does someone else process your personal information?": https://www.michalsons.com/focus-areas/privacy-and-data-protection/does-someone-else-process-your-personal-information
- Information Regulator of South Africa: https://inforegulator.org.za/
- Protection of Personal Information Act 4 of 2013: https://www.gov.za/documents/protection-personal-information-act

---

*VulaTrust is being developed incrementally. The research, prototype and evaluation will determine which proposed features are useful enough to keep.*
