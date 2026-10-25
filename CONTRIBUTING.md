# Contributing to VulaTrust

Thank you for your interest. VulaTrust is a small research and learning project, so the process is light.

## Reporting a bug

Open a GitHub issue and include:

1. **What happened** and **what you expected**.
2. **Steps to reproduce**, starting from a fresh database if you can.
3. **A small synthetic CSV or example** if the bug involves an import. Please do not attach real company data.
4. Your Python version and operating system.

## Reporting a security problem

Please do **not** open a public issue for a security problem. Contact the maintainer privately instead (add your preferred contact here before publishing). Describe what you found and how to reproduce it. See `docs/security-notes.md` for what is already covered and what is known to be missing.

## Proposing a change

1. Open an issue first describing the problem and your idea, so effort is not wasted.
2. Fork the repository and create a branch.
3. Make your change **with tests**. Every behaviour in this project has a test, and pull requests without one will be asked to add it.
4. Run the whole suite and make sure it passes:
   ```
   python -m pytest
   ```
5. Update the relevant file in `docs/` if you changed behaviour, scoring or the data model.
6. Open a pull request and say what changed and why.

## Ground rules

- **Synthetic data only.** Never commit real vendor, employee, customer or company information, or any credentials.
- **Unknown is not safe.** Anything that decides a risk result must treat a missing answer as unknown, never as "no".
- **Explainable over clever.** A business owner should be able to see why something was flagged.
- **Escape everything.** Templates must not turn user text into markup. New forms must include the CSRF token (a test checks this).
- Keep the scoring in `app/scoring.py` free of database, web and clock code.

## Good first contributions

- More synthetic test scenarios for the CSV check and matching.
- Documentation and usability improvements.
- The stretch features listed in the README (login and roles, an audit log, direct Google Workspace or Microsoft 365 import, CSV export, review reminders).
