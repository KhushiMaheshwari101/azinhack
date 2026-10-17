"""Snapshot and compare a selected public policy page."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from ..config import get_settings
from . import storage, tinyfish_client
from .domain import belongs_to_domain, require_company_url
from .change_classifier import classify_change


class MonitorError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def normalize_page_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def text_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def _excerpt(text: str, start: int, end: int, limit: int = 360) -> str:
    if not text:
        return "(no text)"
    left = max(0, start - limit // 3)
    right = min(len(text), max(end, start + 1) + (limit * 2 // 3))
    value = text[left:right].strip()
    if len(value) > limit:
        value = value[:limit].rstrip() + "…"
    if left:
        value = "…" + value
    if right < len(text):
        value += "…"
    return value


def compare_text(old_text: str, new_text: str) -> dict[str, Any]:
    old_normalized, new_normalized = normalize_page_text(old_text), normalize_page_text(new_text)
    changed = text_hash(old_normalized) != text_hash(new_normalized)
    if not changed:
        return {"changed": False, "category": "none", "old_excerpt": "", "new_excerpt": ""}
    matcher = SequenceMatcher(a=old_normalized, b=new_normalized, autojunk=True)
    hunks = [op for op in matcher.get_opcodes() if op[0] != "equal"][:4]
    old_parts, new_parts = [], []
    for index, (_, a1, a2, b1, b2) in enumerate(hunks, start=1):
        old_parts.append(f"[Change {index}] {_excerpt(old_normalized, a1, a2)}")
        new_parts.append(f"[Change {index}] {_excerpt(new_normalized, b1, b2)}")
    old_excerpt = "\n\n".join(old_parts)[:1800]
    new_excerpt = "\n\n".join(new_parts)[:1800]
    prediction = classify_change(old_excerpt, new_excerpt)
    return {"changed": True, "category": prediction["category"], "category_confidence": prediction["confidence"], "category_method": prediction["method"], "old_excerpt": old_excerpt, "new_excerpt": new_excerpt}


def _fetch_allowed_page(
    page_url: str, domain: str, *, etag: str | None = None, last_modified: str | None = None,
) -> dict[str, Any]:
    require_company_url(page_url, domain)
    try:
        page = tinyfish_client.fetch_page(
            page_url,
            max_chars=get_settings().max_page_chars,
            etag=etag,
            last_modified=last_modified,
        )
    except Exception as exc:
        raise MonitorError("provider_error", "The public page could not be fetched.") from exc
    if not page:
        raise MonitorError("empty_page", "The page returned no readable text.")
    if not page.get("not_modified") and not page.get("text", "").strip():
        raise MonitorError("empty_page", "The page returned no readable text.")
    final_url = page.get("final_url") or page_url
    if not belongs_to_domain(final_url, domain):
        raise MonitorError("domain_redirect", "The page redirected outside the submitted company domain.")
    page["final_url"] = final_url
    return page


def create_monitor(*, company_name: str, domain: str, page_url: str, frequency: str) -> dict[str, Any]:
    page = _fetch_allowed_page(page_url, domain)
    normalized = normalize_page_text(page["text"])
    if not normalized:
        raise MonitorError("empty_page", "The page returned no readable text.")
    record = storage.create_monitor(
        company_name=company_name,
        domain=domain,
        page_url=page["final_url"],
        frequency=frequency,
        page_title=page.get("title", ""),
        page_text=page["text"],
        normalized_hash=text_hash(normalized),
        etag=page.get("etag"),
        last_modified=page.get("last_modified"),
    )
    return {"monitor": record, "status": "baseline_saved", "source_url": page["final_url"]}


def check_monitor(monitor_id: str) -> dict[str, Any]:
    monitor = storage.get_monitor(monitor_id)
    if not monitor:
        raise MonitorError("not_found", "This monitored page was not found.")
    if not monitor["active"]:
        raise MonitorError("inactive", "Monitoring for this page is paused.")
    latest = storage.get_latest_snapshot(monitor_id)
    if not latest:
        raise MonitorError("baseline_missing", "No previous snapshot exists for this page.")
    page = _fetch_allowed_page(
        monitor["page_url"], monitor["official_domain"],
        etag=latest.get("etag"), last_modified=latest.get("last_modified"),
    )
    if page.get("not_modified"):
        page["text"] = latest["page_text"]
        page["title"] = page.get("title") or latest["page_title"]
        page["etag"] = page.get("etag") or latest.get("etag")
        page["last_modified"] = page.get("last_modified") or latest.get("last_modified")
    diff = compare_text(latest["page_text"], page["text"])
    result = storage.record_successful_check(
        monitor_id=monitor_id,
        page_url=page["final_url"],
        page_title=page.get("title", ""),
        page_text=page["text"],
        normalized_hash=text_hash(normalize_page_text(page["text"])),
        etag=page.get("etag"),
        last_modified=page.get("last_modified"),
        changed=diff["changed"],
        category=diff["category"],
        category_confidence=diff.get("category_confidence", 0),
        category_method=diff.get("category_method", "keyword_fallback"),
        old_excerpt=diff["old_excerpt"],
        new_excerpt=diff["new_excerpt"],
    )
    result["source_url"] = page["final_url"]
    return result


def create_demo_monitor(*, company_name: str, domain: str, page_url: str, frequency: str) -> dict[str, Any]:
    baseline_text = (
        f"Official Grievance Redressal Policy for {company_name}.\n"
        f"Grievance Officer: Designated Consumer Redressal Team.\n"
        f"Official contact email: care@{domain}.\n"
        f"Acknowledgement timeline: within 48 hours of ticket creation.\n"
        f"Resolution timeline: within 30 days.\n"
        f"Return & Refund Policy: Consumers can request an exchange or full refund within 14 calendar days of delivery."
    )
    normalized = normalize_page_text(baseline_text)
    record = storage.create_monitor(
        company_name=company_name,
        domain=domain,
        page_url=page_url,
        frequency=frequency,
        page_title=f"{company_name} - Grievance & Policy Baseline",
        page_text=baseline_text,
        normalized_hash=text_hash(normalized),
    )
    return {"monitor": record, "status": "baseline_saved", "source_url": page_url}


def check_demo_monitor(monitor_id: str) -> dict[str, Any]:
    monitor = storage.get_monitor(monitor_id)
    if not monitor:
        raise MonitorError("not_found", "This monitored page was not found.")
    if not monitor["active"]:
        raise MonitorError("inactive", "Monitoring for this page is paused.")
    latest = storage.get_latest_snapshot(monitor_id)
    if not latest:
        raise MonitorError("baseline_missing", "No previous snapshot exists for this page.")
    new_text = (
        f"Official Grievance Redressal Policy for {monitor['company_name']}.\n"
        f"Grievance Officer: Designated Consumer Redressal Team.\n"
        f"Official contact email: help@{monitor['official_domain']}.\n"
        f"Acknowledgement timeline: within 48 hours of ticket creation.\n"
        f"Resolution timeline: within 30 days.\n"
        f"Return & Refund Policy: Consumers can request an exchange or partial store credit within 48 hours of delivery."
    )
    diff = compare_text(latest["page_text"], new_text)
    result = storage.record_successful_check(
        monitor_id=monitor_id,
        page_url=monitor["page_url"],
        page_title=f"{monitor['company_name']} - Updated Policy Snapshot",
        page_text=new_text,
        normalized_hash=text_hash(normalize_page_text(new_text)),
        etag=None,
        last_modified=None,
        changed=diff["changed"],
        category=diff["category"],
        category_confidence=diff.get("category_confidence", 0.94),
        category_method=diff.get("category_method", "tfidf_logistic_regression"),
        old_excerpt=diff["old_excerpt"],
        new_excerpt=diff["new_excerpt"],
    )
    result["source_url"] = monitor["page_url"]
    return result



def run_due_checks(limit: int = 20) -> int:
    due = storage.due_monitors(limit=limit)
    for monitor in due:
        try:
            check_monitor(monitor["id"])
        except MonitorError as exc:
            storage.record_failed_check(monitor["id"], exc.code)
        except Exception:
            storage.record_failed_check(monitor["id"], "provider_error")
    return len(due)
