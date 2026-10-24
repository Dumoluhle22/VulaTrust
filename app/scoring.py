"""Vendor risk score (issues 15 and 16).

A pure function: facts in, score out. No database, no web and no clock (today's
date is passed in), so the same input always gives the same output.

Principles
* Every factor is explained, so a business owner can see why a vendor is flagged.
* Missing information is never treated as safe. An unknown input adds HALF of
  the factor's points and is labelled "unverified".
* The score says where to look first. It is not proof that a vendor is secure
  or insecure.
"""
import math
from dataclasses import dataclass, field
from datetime import date

from app.models import AgreementStatus, HostingLocation, TriState
from app.reviews import NEVER_REVIEWED, OVERDUE, review_status

# ---- configuration: change the numbers here and nowhere else ---------------
WEIGHTS = {
    "personal_no_agreement": 35,
    "privileged_access": 20,
    "no_owner": 15,
    "review_overdue": 15,
    "hosted_outside_sa": 10,
    "many_users": 5,
}
LABELS = {
    "personal_no_agreement": "Personal information without a signed operator agreement",
    "privileged_access": "Broad (privileged) access",
    "no_owner": "No owner assigned",
    "review_overdue": "Review overdue or never done",
    "hosted_outside_sa": "Hosted outside South Africa",
    "many_users": "Many users connected",
}
UNKNOWN_FRACTION = 0.5   # share of a factor's points added when the input is unknown
SCORE_CAP = 100
HIGH_AT = 70             # 70 or more is high
MEDIUM_AT = 40           # 40 to 69 is medium, below 40 is low
MANY_USERS_AT = 5

CONFIRMED = "confirmed"
UNVERIFIED = "unverified"


@dataclass(frozen=True)
class AppFacts:
    user_count: int
    privileged: TriState


@dataclass(frozen=True)
class VendorFacts:
    handles_personal_info: TriState = TriState.UNKNOWN
    operator_agreement_status: AgreementStatus = AgreementStatus.UNKNOWN
    hosting_location: HostingLocation = HostingLocation.UNKNOWN
    owner: str | None = None
    last_reviewed: date | None = None
    next_review_due: date | None = None
    applications: tuple[AppFacts, ...] = ()


@dataclass(frozen=True)
class FactorResult:
    key: str
    label: str
    points: float
    max_points: int
    status: str   # CONFIRMED or UNVERIFIED
    why: str


@dataclass(frozen=True)
class Completeness:
    known: int
    total: int
    missing: tuple[str, ...]


@dataclass(frozen=True)
class ScoreResult:
    score: int
    level: str                          # "high", "medium" or "low"
    factors: tuple[FactorResult, ...]   # only the factors that added points
    not_applied: tuple[str, ...]        # labels of factors that were checked and added nothing
    completeness: Completeness


def level_for(score: int) -> str:
    if score >= HIGH_AT:
        return "high"
    if score >= MEDIUM_AT:
        return "medium"
    return "low"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _applies(key: str, applies: bool | None, confirmed: str, unverified: str):
    """True = full points, None = unknown (half points), False = nothing."""
    if applies is False:
        return None
    if applies is True:
        return FactorResult(key, LABELS[key], WEIGHTS[key], WEIGHTS[key], CONFIRMED, confirmed)
    return FactorResult(
        key, LABELS[key], WEIGHTS[key] * UNKNOWN_FRACTION, WEIGHTS[key], UNVERIFIED, unverified
    )


def score_vendor(facts: VendorFacts, today: date) -> ScoreResult:
    apps = facts.applications
    results: list[tuple[str, FactorResult | None]] = []

    # 1. Personal information and no signed operator agreement
    status, personal = facts.operator_agreement_status, facts.handles_personal_info
    if status == AgreementStatus.SIGNED or personal == TriState.NO:
        applies = False
    elif personal == TriState.YES and status in (AgreementStatus.NONE, AgreementStatus.REQUESTED):
        applies = True
    else:
        applies = None
    results.append((
        "personal_no_agreement",
        _applies(
            "personal_no_agreement", applies,
            f"Handles personal information and the operator agreement is '{status.value}'.",
            f"May handle personal information without a signed agreement "
            f"(personal information: {personal.value}, agreement: {status.value}).",
        ),
    ))

    # 2. Privileged access, taken across all of the vendor's applications
    privileged = [app.privileged for app in apps]
    if TriState.YES in privileged:
        applies = True
    elif not privileged or TriState.UNKNOWN in privileged:
        applies = None
    else:
        applies = False
    yes_count = privileged.count(TriState.YES)
    unknown_count = privileged.count(TriState.UNKNOWN)
    results.append((
        "privileged_access",
        _applies(
            "privileged_access", applies,
            f"{_plural(yes_count, 'application')} with broad access.",
            "No applications are recorded, so privileged access is unverified."
            if not privileged
            else f"Privileged access is unknown for {_plural(unknown_count, 'application')}.",
        ),
    ))

    # 3. No owner
    has_owner = bool(facts.owner and facts.owner.strip())
    results.append((
        "no_owner",
        _applies("no_owner", not has_owner, "No owner is assigned to this vendor.", ""),
    ))

    # 4. Review overdue, or never reviewed
    review = review_status(facts.last_reviewed, facts.next_review_due, today)
    if review == NEVER_REVIEWED:
        why = "This vendor has never been reviewed."
    else:
        why = f"The review was due on {facts.next_review_due.isoformat()}." if facts.next_review_due else ""
    results.append((
        "review_overdue",
        _applies("review_overdue", review in (NEVER_REVIEWED, OVERDUE), why, ""),
    ))

    # 5. Hosted outside South Africa
    hosting = facts.hosting_location
    if hosting == HostingLocation.OUTSIDE_SOUTH_AFRICA:
        applies = True
    elif hosting == HostingLocation.UNKNOWN:
        applies = None
    else:
        applies = False
    results.append((
        "hosted_outside_sa",
        _applies(
            "hosted_outside_sa", applies,
            "Data is hosted outside South Africa.",
            "The hosting location is unknown.",
        ),
    ))

    # 6. Many users, summed across applications
    users = sum(app.user_count for app in apps)
    results.append((
        "many_users",
        _applies(
            "many_users", users >= MANY_USERS_AT,
            f"{_plural(users, 'user')} connected across its applications.", "",
        ),
    ))

    factors = tuple(result for _key, result in results if result is not None)
    not_applied = tuple(LABELS[key] for key, result in results if result is None)
    raw = min(SCORE_CAP, sum(f.points for f in factors))
    score = math.floor(raw + 0.5)  # round half up, so 67.5 becomes 68

    checks = [
        ("Handles personal information", personal != TriState.UNKNOWN),
        ("Hosting location", hosting != HostingLocation.UNKNOWN),
        ("Operator agreement status", status != AgreementStatus.UNKNOWN),
        ("Owner", has_owner),
        ("Last reviewed", facts.last_reviewed is not None),
        ("Next review due", facts.next_review_due is not None),
        ("Privileged access", bool(privileged) and TriState.UNKNOWN not in privileged),
    ]
    completeness = Completeness(
        known=sum(1 for _name, known in checks if known),
        total=len(checks),
        missing=tuple(name for name, known in checks if not known),
    )
    return ScoreResult(score, level_for(score), factors, not_applied, completeness)


def facts_from_vendor(vendor) -> VendorFacts:
    """Copy what the score needs out of a Vendor (and its applications)."""
    return VendorFacts(
        handles_personal_info=vendor.handles_personal_info,
        operator_agreement_status=vendor.operator_agreement_status,
        hosting_location=vendor.hosting_location,
        owner=vendor.owner,
        last_reviewed=vendor.last_reviewed,
        next_review_due=vendor.next_review_due,
        applications=tuple(AppFacts(a.user_count, a.privileged) for a in vendor.applications),
    )
