import pytest

from app.domains import is_valid_domain, normalise_domain


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("paytrack.example", "paytrack.example"),
        ("PayTrack.EXAMPLE", "paytrack.example"),
        ("www.clinicnotes.example", "clinicnotes.example"),
        ("https://quicksign.example/app", "quicksign.example"),
        ("HTTP://WWW.Example.com:8080/a/b?x=1#top", "example.com"),
        ("  spaced.example  ", "spaced.example"),
        ("user@mail.example", "mail.example"),
        ("trailing.example.", "trailing.example"),
        ("app.clinicnotes.example", "app.clinicnotes.example"),
    ],
)
def test_normalise_domain(raw, expected):
    assert normalise_domain(raw) == expected


@pytest.mark.parametrize("domain", ["paytrack.example", "a-b.co.za", "app.vendor.example"])
def test_valid_domains(domain):
    assert is_valid_domain(domain)


@pytest.mark.parametrize(
    "domain",
    ["", "localhost", "paytrack", "not a domain", "-bad.example", "bad-.example",
     "1.2.3.4", "two..dots.example", "a" * 300 + ".example"],
)
def test_invalid_domains(domain):
    assert not is_valid_domain(domain)
