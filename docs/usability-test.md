# Usability test (issue 22)

Purpose: find out whether someone **without a cybersecurity background** can use VulaTrust's key functions without help. The goal is to find problems, not to prove the app is good. Report failures honestly: a test that finds and fixes problems is worth more than one where everyone succeeds.

**Aim for 3 people.** Friends or family who do not work in IT are ideal.

## Setup (before each person)

1. Stop the app, delete `vulatrust.db`, run `python -m app.seed`, start the app.
2. Open http://127.0.0.1:8000 and keep `sample_data/apps.csv` where they can find it.
3. Have this sheet and a timer ready.

## What to say

> I am testing the software, not you. If something is confusing, that is a problem with the software. Please think aloud as you go. I can't help during the tasks, but I will note where you get stuck. You can stop at any time.

Do not record names. Use "Participant 1, 2, 3".

## Tasks

Give each task on its own, and do not explain how.

| # | Task | Done when | Aim |
|---|---|---|---|
| 1 | "Add a new vendor called **Example Supplies**. It handles customers' personal information and it is hosted in South Africa. You have no signed agreement with them yet." | The vendor exists with personal information Yes, hosting South Africa, agreement None or Requested | Under 3 minutes, no help |
| 2 | "You have a list of apps in a file called apps.csv. Import it." | The import is confirmed and the batch page appears | Under 4 minutes, no help |
| 3 | "Find which vendors have a review that is overdue or never done." | The person names the vendors, from the dashboard or vendor pages (ChatBridge, LedgerLite, MailBlast and ClinicNotes) | Under 2 minutes, no help |

## Observation sheet

One copy per participant.

| | Task 1 | Task 2 | Task 3 |
|---|---|---|---|
| Completed without help? (yes / yes with hints / no) | | | |
| Time taken | | | |
| Wrong turns or hesitations | | | |
| Things they said aloud | | | |
| Problems noticed | | | |

## Questions at the end

1. What was the most confusing part?
2. Without looking, what does "unknown" mean in the app?
3. What does the score on a vendor page tell you? (Listen for whether they think it proves a vendor is safe or unsafe.)
4. What do you think "unassigned" means?
5. Would you use this for a real business? What would make you? What would stop you?

## Results (fill in after all participants)

| Task | Participant 1 | Participant 2 | Participant 3 | Success rate |
|---|---|---|---|---|
| 1 Add a vendor | | | | /3 |
| 2 Import the file | | | | /3 |
| 3 Find overdue reviews | | | | /3 |

Write up in `docs/usability-results.md`:

- What worked and what failed, including failures.
- The problems you saw, ordered by how many people hit them.
- **At least one fix you made because of what you observed**, and the change in the app.
- The limits of the test: three people, who they were, a short session.

## Likely problem areas to watch

These are guesses to look out for, not conclusions:

- Whether people understand that **Check file** saves nothing and **Confirm import** does.
- Whether "unknown" and "unverified" make sense, and whether people think Unknown is the same as No.
- Whether the signed-agreement date rule (a date is needed only when the status is Signed) causes errors.
- Whether people expect the dashboard to be clickable.
