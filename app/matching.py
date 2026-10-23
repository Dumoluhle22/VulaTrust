"""Match an imported application's domain to a vendor (issue 10).

Rules (also written in sample_data/README.md):

1. Exact: the application's domain equals a vendor's primary domain.
2. Subdomain: otherwise the application's domain ends with "." plus a vendor's
   primary domain (app.paytrack.example belongs to paytrack.example). If more
   than one vendor domain fits, the most specific (longest) one wins.
3. Anything else stays unassigned and is never guessed: a blank domain, a
   domain no vendor uses, or a domain that more than one vendor claims.

Whole labels only: notpaytrack.example does NOT match paytrack.example.
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from app.domains import normalise_domain

EXACT = "exact_domain"
SUBDOMAIN = "subdomain"


@dataclass(frozen=True)
class MatchResult:
    vendor_id: int | None
    method: str | None = None  # EXACT or SUBDOMAIN when matched
    reason: str | None = None  # why it stayed unassigned


class VendorMatcher:
    def __init__(self, vendor_domains: Iterable[tuple[int, str | None]]):
        self._by_domain: dict[str, list[int]] = defaultdict(list)
        for vendor_id, domain in vendor_domains:
            cleaned = normalise_domain(domain or "")
            if cleaned and "." in cleaned:  # a bare "com" would match far too much
                self._by_domain[cleaned].append(vendor_id)

    def match(self, domain: str | None) -> MatchResult:
        cleaned = normalise_domain(domain or "")
        if not cleaned:
            return MatchResult(None, reason="No domain given")

        labels = cleaned.split(".")
        # the domain itself first, then each parent with at least two labels
        candidates = [cleaned] + [
            ".".join(labels[i:]) for i in range(1, len(labels) - 1)
        ]
        for position, candidate in enumerate(candidates):
            vendor_ids = self._by_domain.get(candidate)
            if not vendor_ids:
                continue
            if len(vendor_ids) > 1:
                return MatchResult(None, reason="More than one vendor uses this domain")
            return MatchResult(vendor_ids[0], EXACT if position == 0 else SUBDOMAIN)
        return MatchResult(None, reason="No vendor uses this domain")
