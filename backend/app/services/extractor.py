"""Conservative extraction: every returned value carries its verbatim source quote."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

PATTERNS = {
    "officer_name": re.compile(r"(?:grievance officer|grievance redressal officer|nodal officer|customer grievance officer)\s*[:\-–]\s*([A-Z][A-Za-z.' -]{2,80})", re.I),
    "designation": re.compile(r"(?:designation|title)\s*[:\-–]\s*([^\n]{2,100})", re.I),
    "email": re.compile(r"[A-Z0-9._%+\-]+\s*(?:@|\[at\]|\(at\))\s*[A-Z0-9.\-]+\s*(?:\.|\[dot\]|\(dot\))\s*[A-Z]{2,}", re.I),
    "phone": re.compile(r"(?:phone|telephone|contact number|mobile|helpline)\s*[:\-–]?\s*(\+?\d[\d ()-]{7,18}\d)", re.I),
}


def _canonical(value: str) -> str:
    return re.sub(r"\s+", "", value.casefold()).replace("[at]", "@").replace("(at)", "@").replace("[dot]", ".").replace("(dot)", ".")


def extract_fields(text: str, source_url: str, title: str = "") -> dict[str, dict[str, Any]]:
    findings: dict[str, dict[str, Any]] = {}
    for field, pattern in PATTERNS.items():
        match = pattern.search(text)
        if not match:
            findings[field] = {"value": None, "status": "unclear", "evidence": None}
            continue
        value = (match.group(1) if match.lastindex else match.group(0)).strip().rstrip(".,;|")
        quote = text[max(0, match.start() - 100):min(len(text), match.end() + 100)].strip()
        if _canonical(value) not in _canonical(quote):
            findings[field] = {"value": None, "status": "unclear", "evidence": None}
            continue
        findings[field] = {
            "value": value,
            "status": "verified",
            "evidence": {
                "source_url": source_url,
                "page_title": title,
                "quote": quote,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    return findings
