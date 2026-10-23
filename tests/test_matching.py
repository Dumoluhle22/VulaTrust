import pytest

from app.matching import EXACT, SUBDOMAIN, MatchResult, VendorMatcher

VENDORS = [
    (1, "paytrack.example"),
    (2, "clinicnotes.example"),
    (3, "docs.clinicnotes.example"),
]


@pytest.fixture
def matcher():
    return VendorMatcher(VENDORS)


def test_exact_match(matcher):
    assert matcher.match("paytrack.example") == MatchResult(1, EXACT)


def test_matching_ignores_case_www_and_url_decoration(matcher):
    for raw in ["PayTrack.EXAMPLE", "www.paytrack.example", "https://paytrack.example/app?x=1"]:
        assert matcher.match(raw) == MatchResult(1, EXACT), raw


def test_subdomain_match(matcher):
    assert matcher.match("app.paytrack.example") == MatchResult(1, SUBDOMAIN)
    assert matcher.match("a.b.c.paytrack.example") == MatchResult(1, SUBDOMAIN)


def test_most_specific_vendor_domain_wins(matcher):
    assert matcher.match("docs.clinicnotes.example") == MatchResult(3, EXACT)
    assert matcher.match("x.docs.clinicnotes.example") == MatchResult(3, SUBDOMAIN)
    assert matcher.match("x.clinicnotes.example") == MatchResult(2, SUBDOMAIN)


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_domain_is_left_unassigned(matcher, blank):
    result = matcher.match(blank)
    assert result.vendor_id is None
    assert result.method is None
    assert result.reason == "No domain given"


def test_no_matching_vendor_is_left_unassigned(matcher):
    result = matcher.match("unknown.example")
    assert result.vendor_id is None
    assert result.reason == "No vendor uses this domain"


def test_only_whole_labels_match(matcher):
    assert matcher.match("notpaytrack.example").vendor_id is None
    assert matcher.match("paytrack.example.evil.test").vendor_id is None
    assert matcher.match("paytrack.examples").vendor_id is None


def test_a_parent_domain_never_matches_a_more_specific_vendor(matcher):
    # clinicnotes.example must not be linked to the docs.clinicnotes.example vendor
    assert matcher.match("clinicnotes.example") == MatchResult(2, EXACT)


def test_ambiguous_domain_is_left_unassigned_and_never_guessed():
    matcher = VendorMatcher([(1, "shared.example"), (2, "shared.example")])
    for domain in ["shared.example", "app.shared.example"]:
        result = matcher.match(domain)
        assert result.vendor_id is None, domain
        assert result.reason == "More than one vendor uses this domain"


def test_vendors_without_a_usable_domain_are_ignored():
    matcher = VendorMatcher([(1, None), (2, ""), (3, "com"), (4, "paytrack.example")])
    assert matcher.match("anything.com").vendor_id is None  # a bare "com" claims nothing
    assert matcher.match("paytrack.example").vendor_id == 4


def test_vendor_domains_are_cleaned_too():
    matcher = VendorMatcher([(1, "HTTPS://WWW.PayTrack.example/")])
    assert matcher.match("paytrack.example") == MatchResult(1, EXACT)


def test_empty_matcher_matches_nothing():
    assert VendorMatcher([]).match("paytrack.example").vendor_id is None
