from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

import app.scoring as scoring
from app.csv_import import check_csv
from app.importer import apply_import, build_plan
from app.models import AgreementStatus, HostingLocation, TriState, Vendor
from app.scoring import AppFacts, VendorFacts, facts_from_vendor, level_for, score_vendor
from app.seed import load_vendors

TODAY = date(2026, 10, 13)
SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "apps.csv"

# A vendor with nothing wrong: every factor adds 0.
CLEAN = VendorFacts(
    handles_personal_info=TriState.NO,
    operator_agreement_status=AgreementStatus.NONE,
    hosting_location=HostingLocation.SOUTH_AFRICA,
    owner="Thandi",
    last_reviewed=date(2026, 9, 1),
    next_review_due=date(2027, 9, 1),
    applications=(AppFacts(1, TriState.NO),),
)
# A vendor where every factor applies at full strength.
WORST = VendorFacts(
    handles_personal_info=TriState.YES,
    operator_agreement_status=AgreementStatus.NONE,
    hosting_location=HostingLocation.OUTSIDE_SOUTH_AFRICA,
    owner=None,
    last_reviewed=None,
    next_review_due=None,
    applications=(AppFacts(10, TriState.YES),),
)


def points(result, key):
    return next((f.points for f in result.factors if f.key == key), 0)


def status(result, key):
    return next((f.status for f in result.factors if f.key == key), None)


# ---- baseline -------------------------------------------------------------------

def test_a_clean_vendor_scores_zero_and_is_fully_known():
    result = score_vendor(CLEAN, TODAY)
    assert result.score == 0
    assert result.level == "low"
    assert result.factors == ()
    assert len(result.not_applied) == 6
    assert (result.completeness.known, result.completeness.total) == (7, 7)
    assert result.completeness.missing == ()


# ---- factor 1: personal information and no signed agreement (35) ------------------

@pytest.mark.parametrize("agreement", [AgreementStatus.NONE, AgreementStatus.REQUESTED])
def test_personal_info_without_a_signed_agreement_is_35_confirmed(agreement):
    result = score_vendor(replace(CLEAN, handles_personal_info=TriState.YES, operator_agreement_status=agreement), TODAY)
    assert points(result, "personal_no_agreement") == 35
    assert status(result, "personal_no_agreement") == "confirmed"
    assert result.score == 35


def test_a_signed_agreement_or_no_personal_info_removes_the_factor():
    signed = replace(CLEAN, handles_personal_info=TriState.YES, operator_agreement_status=AgreementStatus.SIGNED)
    assert score_vendor(signed, TODAY).score == 0
    no_personal = replace(CLEAN, handles_personal_info=TriState.NO, operator_agreement_status=AgreementStatus.NONE)
    assert score_vendor(no_personal, TODAY).score == 0
    unknown_but_signed = replace(CLEAN, handles_personal_info=TriState.UNKNOWN, operator_agreement_status=AgreementStatus.SIGNED)
    assert score_vendor(unknown_but_signed, TODAY).score == 0


@pytest.mark.parametrize(
    "personal, agreement",
    [
        (TriState.YES, AgreementStatus.UNKNOWN),
        (TriState.UNKNOWN, AgreementStatus.NONE),
        (TriState.UNKNOWN, AgreementStatus.REQUESTED),
        (TriState.UNKNOWN, AgreementStatus.UNKNOWN),
    ],
)
def test_unknown_inputs_add_half_the_points_and_are_unverified(personal, agreement):
    result = score_vendor(replace(CLEAN, handles_personal_info=personal, operator_agreement_status=agreement), TODAY)
    assert points(result, "personal_no_agreement") == 17.5
    assert status(result, "personal_no_agreement") == "unverified"
    assert result.score == 18  # 17.5 rounded half up


# ---- factor 2: privileged access (20) ------------------------------------------------

def test_privileged_access_across_applications():
    def with_apps(*privs):
        return score_vendor(replace(CLEAN, applications=tuple(AppFacts(1, p) for p in privs)), TODAY)

    assert points(with_apps(TriState.YES), "privileged_access") == 20
    assert status(with_apps(TriState.NO, TriState.YES), "privileged_access") == "confirmed"
    assert points(with_apps(TriState.YES, TriState.UNKNOWN), "privileged_access") == 20  # a known yes wins
    assert points(with_apps(TriState.NO, TriState.NO), "privileged_access") == 0
    unknown = with_apps(TriState.NO, TriState.UNKNOWN)
    assert points(unknown, "privileged_access") == 10
    assert status(unknown, "privileged_access") == "unverified"


def test_no_applications_means_privileged_access_is_unverified():
    result = score_vendor(replace(CLEAN, applications=()), TODAY)
    assert points(result, "privileged_access") == 10
    factor = next(f for f in result.factors if f.key == "privileged_access")
    assert "No applications are recorded" in factor.why


# ---- factors 3 to 6 -------------------------------------------------------------------------

@pytest.mark.parametrize("owner", [None, "", "   "])
def test_no_owner_is_15(owner):
    result = score_vendor(replace(CLEAN, owner=owner), TODAY)
    assert (points(result, "no_owner"), status(result, "no_owner")) == (15, "confirmed")


def test_review_factor_covers_never_and_overdue_but_not_today_or_future():
    def review(last, nxt):
        return points(score_vendor(replace(CLEAN, last_reviewed=last, next_review_due=nxt), TODAY), "review_overdue")

    assert review(None, None) == 15                         # never reviewed
    assert review(date(2026, 1, 1), date(2026, 10, 12)) == 15  # overdue yesterday
    assert review(date(2026, 1, 1), date(2026, 10, 13)) == 0   # due today
    assert review(date(2026, 1, 1), date(2027, 1, 1)) == 0
    assert review(date(2026, 1, 1), None) == 0              # reviewed, no schedule


def test_hosting_location_factor():
    def hosting(value):
        return score_vendor(replace(CLEAN, hosting_location=value), TODAY)

    assert points(hosting(HostingLocation.OUTSIDE_SOUTH_AFRICA), "hosted_outside_sa") == 10
    unknown = hosting(HostingLocation.UNKNOWN)
    assert (points(unknown, "hosted_outside_sa"), status(unknown, "hosted_outside_sa")) == (5, "unverified")
    assert points(hosting(HostingLocation.SOUTH_AFRICA), "hosted_outside_sa") == 0


def test_user_count_is_summed_across_applications():
    def users(*counts):
        apps = tuple(AppFacts(c, TriState.NO) for c in counts)
        return points(score_vendor(replace(CLEAN, applications=apps), TODAY), "many_users")

    assert users(4) == 0
    assert users(5) == 5
    assert users(3, 2) == 5   # neither application alone reaches 5
    assert users(2, 2) == 0


# ---- the sample vendors (documented in sample_data/README.md) --------------------------------

EXPECTED_SAMPLE_SCORES = {
    "PayTrack": (5, "low"),
    "ClinicNotes": (85, "high"),
    "QuickSign": (15, "low"),
    "ChatBridge": (68, "medium"),   # 67.5 before rounding
    "Brightlearn LMS": (40, "medium"),  # exactly on the boundary
    "MailBlast": (60, "medium"),
    "DesignHub": (15, "low"),
    "LedgerLite": (50, "medium"),
}


def test_sample_vendors_score_as_documented(db):
    load_vendors(db)
    plan = build_plan(db, check_csv(SAMPLE.read_bytes(), "apps.csv"))
    apply_import(db, "apps.csv", plan)

    actual = {}
    for vendor in db.query(Vendor):
        result = score_vendor(facts_from_vendor(vendor), TODAY)
        actual[vendor.name] = (result.score, result.level)
    assert actual == EXPECTED_SAMPLE_SCORES


# ---- scenarios from issue 17 --------------------------------------------------------------------

def test_scenario_personal_info_with_no_signed_agreement_scores_at_least_35():
    for agreement in (AgreementStatus.NONE, AgreementStatus.REQUESTED):
        facts = replace(CLEAN, handles_personal_info=TriState.YES, operator_agreement_status=agreement)
        assert score_vendor(facts, TODAY).score >= 35


def test_scenario_adding_a_signed_agreement_lowers_the_score_by_35():
    before = replace(CLEAN, handles_personal_info=TriState.YES, operator_agreement_status=AgreementStatus.NONE)
    after = replace(before, operator_agreement_status=AgreementStatus.SIGNED)
    assert score_vendor(before, TODAY).score - score_vendor(after, TODAY).score == 35


def test_scenario_assigning_an_owner_lowers_the_score_by_15():
    before = replace(CLEAN, owner=None)
    after = replace(before, owner="Sipho")
    assert score_vendor(before, TODAY).score - score_vendor(after, TODAY).score == 15


def test_scenario_a_recent_review_removes_the_overdue_points():
    before = replace(CLEAN, last_reviewed=None, next_review_due=None)
    after = replace(before, last_reviewed=date(2026, 9, 20), next_review_due=date(2027, 9, 20))
    assert score_vendor(before, TODAY).score - score_vendor(after, TODAY).score == 15


def test_scenario_an_all_unknown_vendor_is_not_rated_low_and_shows_low_completeness():
    result = score_vendor(VendorFacts(), TODAY)
    assert result.level != "low"
    assert result.score == 63   # 62.5: personal 17.5, privileged 10, owner 15, review 15, hosting 5
    assert result.completeness.known == 0
    assert result.completeness.missing == (
        "Handles personal information", "Hosting location", "Operator agreement status",
        "Owner", "Last reviewed", "Next review due", "Privileged access",
    )


def test_scenario_every_factor_together_reaches_exactly_100():
    result = score_vendor(WORST, TODAY)
    assert result.score == 100
    assert result.level == "high"
    assert len(result.factors) == 6
    assert all(f.status == "confirmed" for f in result.factors)


def test_scenario_the_cap_holds_even_if_the_weights_are_raised(monkeypatch):
    monkeypatch.setitem(scoring.WEIGHTS, "personal_no_agreement", 90)
    assert score_vendor(WORST, TODAY).score == 100


def test_scenario_level_boundaries():
    assert [level_for(n) for n in (0, 39, 40, 69, 70, 100)] == ["low", "low", "medium", "medium", "high", "high"]
    forty = replace(CLEAN, handles_personal_info=TriState.YES, operator_agreement_status=AgreementStatus.NONE,
                    applications=(AppFacts(5, TriState.NO),))
    assert score_vendor(forty, TODAY).score == 40 and score_vendor(forty, TODAY).level == "medium"
    seventy = replace(CLEAN, handles_personal_info=TriState.YES, operator_agreement_status=AgreementStatus.NONE,
                      owner=None, applications=(AppFacts(1, TriState.YES),))
    assert score_vendor(seventy, TODAY).score == 70 and score_vendor(seventy, TODAY).level == "high"


# ---- general properties ------------------------------------------------------------------------------

def test_the_same_input_always_gives_the_same_output():
    assert score_vendor(WORST, TODAY) == score_vendor(WORST, TODAY)
    assert score_vendor(VendorFacts(), TODAY) == score_vendor(VendorFacts(), TODAY)


def test_the_result_depends_on_the_date_passed_in():
    facts = replace(CLEAN, last_reviewed=date(2026, 1, 1), next_review_due=date(2026, 11, 1))
    assert score_vendor(facts, date(2026, 10, 13)).score == 0
    assert score_vendor(facts, date(2026, 11, 2)).score == 15


def test_explanations_say_why():
    result = score_vendor(WORST, TODAY)
    why = {f.key: f.why for f in result.factors}
    assert "operator agreement is 'none'" in why["personal_no_agreement"]
    assert "1 application with broad access" in why["privileged_access"]
    assert "never been reviewed" in why["review_overdue"]
    assert "10 users" in why["many_users"]
    overdue = score_vendor(replace(CLEAN, last_reviewed=date(2026, 1, 1), next_review_due=date(2026, 5, 1)), TODAY)
    assert "due on 2026-05-01" in next(f.why for f in overdue.factors if f.key == "review_overdue")
