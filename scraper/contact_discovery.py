"""Extract and rank contact addresses that are explicitly published with a job.

This module deliberately never invents likely email addresses.  An SMTP/MX check
cannot prove that a mailbox exists, so only an address visible in the job
description or public job page is persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from typing import Iterable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.!#$%&'*+/=?^`{|}~-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+(?![\w-])", re.IGNORECASE)
# Only rewrite explicitly bracketed obfuscation. Replacing every natural-language
# "at" would turn phrases such as "contact our recruiter at Acme" into nonsense.
OBFUSCATED_AT_RE = re.compile(r"\s*[\[({]\s*(?:at|@)\s*[\])}]\s*", re.IGNORECASE)
OBFUSCATED_DOT_RE = re.compile(r"\s*[\[({]\s*(?:dot|\.)\s*[\])}]\s*", re.IGNORECASE)
ROLE_KEYWORDS = {
    "recruiter": ("recruiter", "recruiting", "talent acquisition", "talent team"),
    "hiring_manager": ("hiring manager", "manager"),
    "hr": ("human resources", " hr ", "hr team", "people team"),
    "company": ("careers", "jobs", "apply", "application", "hiring team"),
}
BLOCKED_LOCAL_PARTS = {"noreply", "no-reply", "donotreply", "do-not-reply", "example", "test"}
JOB_BOARD_DOMAINS = {"linkedin.com", "indeed.com", "google.com", "glassdoor.com", "ziprecruiter.com"}


@dataclass(frozen=True)
class ContactCandidate:
    email: str
    source: str
    contact_type: str
    confidence: int
    context: str


def normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value if "://" in value else f"https://{value}")
    domain = (parsed.hostname or "").lower().strip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def find_company_domain(row: object, fallback_url: str | None = None) -> str | None:
    """Use explicit company URLs only; do not guess domains from company names."""
    getter = getattr(row, "get", lambda _key, default=None: default)
    for key in ("company_url", "company_website", "company_site"):
        domain = normalize_domain(getter(key))
        if domain:
            return domain
    domain = normalize_domain(fallback_url)
    if domain and not any(domain == board or domain.endswith(f".{board}") for board in JOB_BOARD_DOMAINS):
        return domain
    return None


def _deobfuscate(text: str) -> str:
    text = unescape(text or "")
    text = OBFUSCATED_AT_RE.sub("@", text)
    return OBFUSCATED_DOT_RE.sub(".", text)


def _classify(context: str) -> str:
    lowered = f" {context.lower()} "
    for contact_type, keywords in ROLE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return contact_type
    return "other"


def _score(email: str, context: str, company_domain: str | None, source: str, contact_type: str) -> int:
    local_part, domain = email.rsplit("@", 1)
    score = 35 if source == "description" else 30
    # Named recruiting contacts are more relevant than a general careers inbox.
    score += {
        "recruiter": 45,
        "hiring_manager": 42,
        "hr": 40,
        "company": 25,
        "other": 0,
    }[contact_type]
    if company_domain and (domain == company_domain or domain.endswith(f".{company_domain}")):
        score += 20
    if local_part.lower() in {"careers", "jobs", "recruiting", "recruitment", "hr", "hiring"}:
        score += 10
    if "apply" in context.lower() or "contact" in context.lower():
        score += 5
    return min(score, 100)


def _email_context(text: str, match: re.Match[str]) -> str:
    """Use the local sentence/clause so one email does not borrow another's role."""
    left = max(text.rfind(marker, 0, match.start()) for marker in ("\n", "!", "?", ";")) + 1
    # A full stop is treated as a boundary only when followed by whitespace, so
    # dots in email addresses do not cut the context short.
    preceding_stops = list(re.finditer(r"\.\s+", text[:match.start()]))
    if preceding_stops:
        left = max(left, preceding_stops[-1].end())
    following_stop = re.search(r"(?:[!?;]|\.\s+)", text[match.end():])
    right = match.end() + following_stop.start() if following_stop else len(text)
    return " ".join(text[left:right].split())[:500]


def discover_contacts(text: str, *, source: str, company_domain: str | None = None) -> list[ContactCandidate]:
    """Return unique, syntactically valid publicly visible addresses, ranked best first."""
    text = _deobfuscate(text)
    candidates: dict[str, ContactCandidate] = {}
    for match in EMAIL_RE.finditer(text):
        email = match.group(0).lower().rstrip(".,;:)")
        local_part = email.split("@", 1)[0]
        if local_part in BLOCKED_LOCAL_PARTS:
            continue
        context = _email_context(text, match)
        contact_type = _classify(context)
        candidate = ContactCandidate(email, source, contact_type, _score(email, context, company_domain, source, contact_type), context)
        if email not in candidates or candidate.confidence > candidates[email].confidence:
            candidates[email] = candidate
    return sorted(candidates.values(), key=lambda item: (-item.confidence, item.email))


def fetch_public_job_page(url: str, timeout: int = 12) -> str:
    """Fetch one supplied company job page. Fail closed so scraping can continue."""
    parsed = urlparse(url)
    domain = normalize_domain(url)
    if (
        not url
        or parsed.scheme not in {"http", "https"}
        or not domain
        or any(domain == board or domain.endswith(f".{board}") for board in JOB_BOARD_DOMAINS)
    ):
        return ""
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "autojobapply-contact-discovery/1.0"})
        response.raise_for_status()
        if "html" not in response.headers.get("Content-Type", "").lower():
            return ""
        return BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
    except requests.RequestException:
        return ""


def merge_candidates(*collections: Iterable[ContactCandidate]) -> list[ContactCandidate]:
    merged: dict[str, ContactCandidate] = {}
    for candidate in (item for collection in collections for item in collection):
        if candidate.email not in merged or candidate.confidence > merged[candidate.email].confidence:
            merged[candidate.email] = candidate
    return sorted(merged.values(), key=lambda item: (-item.confidence, item.email))
