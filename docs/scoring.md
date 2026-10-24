# How the vendor score works

The score helps a small business decide **which vendor to look at first**. It is not proof that a vendor is secure or insecure, and it is not a legal compliance rating.

The code is in `app/scoring.py`. It is a pure function: facts about a vendor go in, a score comes out. It does not touch the database, the web layer or the system clock (today's date is passed in), so the same input always gives the same result. All weights and thresholds are defined at the top of that file.

## The six factors

| Factor | Points | Applies when |
|---|---|---|
| Personal information without a signed operator agreement | 35 | The vendor handles personal information and the agreement status is none or requested |
| Broad (privileged) access | 20 | Any of the vendor's applications has broad access |
| No owner assigned | 15 | The owner field is empty |
| Review overdue or never done | 15 | The next review date has passed, or the vendor was never reviewed |
| Hosted outside South Africa | 10 | The hosting location is outside South Africa |
| Many users connected | 5 | Five or more users in total across the vendor's applications |

The maximum is exactly 100, and the total is capped at 100 in case the weights are changed.

## Levels

| Score | Level |
|---|---|
| 70 to 100 | High |
| 40 to 69 | Medium |
| 0 to 39 | Low |

## Missing information is never treated as safe

If an input is **unknown**, the factor adds **half** of its points and is labelled **unverified** on the vendor page. For example, a vendor whose personal-information answer is unknown and whose agreement status is none scores 17.5 for the first factor, not 0.

Specific cases:

- Personal information is "no", or the agreement is signed: the first factor adds nothing.
- Personal information is "yes" and the agreement is none or requested: full 35 points.
- Any other combination of unknowns: 17.5 points, unverified.
- Privileged access is unknown for any application, or **no applications are recorded**: 10 points, unverified. (A known "yes" on any application gives the full 20.)
- Hosting location unknown: 5 points, unverified.

Rounding: the total is rounded half up to a whole number at the end, so 67.5 becomes 68.

## Completeness

Each score is shown with how many of seven fields are known, and which are missing:

1. Handles personal information
2. Hosting location
3. Operator agreement status
4. Owner
5. Last reviewed
6. Next review due
7. Privileged access (known only if at least one application is recorded and none has an unknown value)

A vendor can have a middling score and low completeness. That tells you the score may be hiding problems, not that the vendor is fine.

## Review status

| Status | Meaning |
|---|---|
| Never reviewed | No last-reviewed date. Counts as overdue. |
| Overdue | The next review date is before today. A review due today is not overdue yet. |
| Scheduled | The next review date is today or later. |
| Reviewed, but no next review date | Reviewed at least once, no schedule set. Not counted as overdue. |

## Why these weights (draft, for you to confirm and justify)

These reasons are a starting draft. They have not been validated against real incidents, and you should decide whether you agree and say so in your report.

- **The agreement factor is the largest (35)** because POPIA section 21 requires a written contract with an operator that processes personal information, and the business stays responsible for the data. This is the most clearly documented obligation in the project.
- **Privileged access (20)** reflects that broad access (for example a whole mailbox or drive) increases what a compromise or misuse could expose. Aperio and open-SSPM both treat broad scopes as a key risk signal.
- **No owner (15)** and **overdue review (15)** are governance gaps: nobody is accountable and nobody has looked recently. They are certain facts, so they score in full.
- **Hosting outside South Africa (10)** matters for cross-border transfer rules but is a weaker signal on its own, so it scores lower.
- **Many users (5)** is a small exposure indicator. It should not decide a vendor's level alone.

## Known limitations

- The weights and thresholds are judgement calls and are not calibrated against real breaches.
- The score cannot see what a vendor actually does with data, its security practices, or whether an agreement is any good. It only uses what has been recorded.
- A vendor reviewed once with no next review date is not counted as overdue, so it can look healthier than it is.
- "Many users" sums users across applications, and the same person may be counted more than once.
- A vendor with no applications gets half the privileged points because privileged access cannot be verified. That is deliberate, but it can look odd for vendors that genuinely have no connected apps.
