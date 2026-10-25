# Report outline

Suggested structure. Under each heading is what that section should answer.

## 1. Introduction
- The central question: how do businesses understand and manage the security risks created by external vendors and SaaS applications?
- Why it matters for small South African businesses (POPIA sections 19 and 21; the Dis-Chem enforcement notice).
- What you built, in two sentences.

## 2. Background
- Vendor risk and SaaS shadow IT: what they are.
- Who is affected: owners and information officers, staff, data subjects, vendors, the regulator.
- Target industries and why they were chosen (state that this is an assumption).

## 3. Related work and the gap
- Aperio and open-SSPM: what each does (see `docs/related-work.md`, verified against their schemas and code).
- CISO Assistant: what its third-party module does (**you must read this yourself**).
- The gap, stated as narrowly as the evidence allows, and why a spreadsheet is the real alternative.

## 4. Requirements and scope
- The MVP list, the stretch list and what is out of scope.
- The three questions you answered: the gap, the user, the differentiator.

## 5. Design
- Architecture and module map (`docs/data-model.md`).
- The data model, and the rule that unknown is the default and is never safe.
- The scoring model, its weights and why (`docs/scoring.md`).
- Import and matching rules, and the all-or-nothing import.
- Security design (`docs/security-notes.md`).

## 6. Implementation
- Technology and why. How the work was ordered. How a test-first approach, a fixed test date and sample data with known answers kept the documentation and code in step.

## 7. Evaluation
- The results table below.
- Test and coverage figures (`docs/testing.md`).
- Usability test results (`docs/usability-test.md`).

## 8. Limitations
- Use the list in the README and `docs/security-notes.md`. Be specific about what is unproven.

## 9. Future work
- Login and roles, an audit log, direct import from Google Workspace and Microsoft 365, CSV or PDF export, review reminders, follow-up actions, matching confidence.

## 10. Conclusion
- Did you answer the research question? What would you tell a small business owner?

## References and appendices
- Sources from the README. Appendix ideas: the factor table, sample screenshots, the interview findings (anonymised).

---

## Evaluation results to paste into section 7

| Criterion | Result | Evidence |
|---|---|---|
| A CSV of about 20 synthetic applications imports without errors | **Met.** 23 rows read: 16 imported, 1 duplicate and 6 invalid rows reported, none crashed. | `test_importer.py`, `test_import_flow.py` |
| At least 90% of applications that belong to a registered vendor match the correct vendor by domain | **Met, 11 of 11 (100%).** The other 5 imported applications deliberately have no vendor. | `test_importer.py` |
| Unmatched applications remain visible for review | **Met.** Unassigned page, dashboard count and reasons shown. | `test_import_page.py`, `test_assign.py`, `test_dashboard.py` |
| Vendor and application relationships are consistent | **Met.** Foreign keys, ON DELETE SET NULL, tested. | `test_models.py`, `test_vendors.py` |
| Risk scores are reproducible and their factors visible | **Met.** Same input gives the same output. Every factor is shown with its reason. | `test_scoring.py`, `test_vendor_score_pages.py` |
| Personal information with no signed agreement scores at least 35 | **Met.** | `test_scoring.py` |
| Unknown information is flagged and not treated as safe | **Met.** Unknown adds half points, marked unverified. An all-unknown vendor scores 63 (Medium). | `test_scoring.py` |
| Adding an agreement, owner or review lowers the score as expected | **Met.** By 35, 15 and 15 points. | `test_scoring.py`, `test_vendor_score_pages.py` |
| Missing agreements and overdue reviews are identified | **Met.** | `test_dashboard.py` |
| Input validation and database operations pass their tests | **Met.** 333 tests passing, 98% coverage. | all test files |
| People without a cybersecurity background complete the key tasks in a usability test | **Not yet measured.** Complete this from `docs/usability-test.md` and record the result honestly. | |

Be careful with the second row: say plainly that the 90% target was met on a small synthetic file, and that real files will be messier.
