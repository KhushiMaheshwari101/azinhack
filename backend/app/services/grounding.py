"""Reject any extracted value that cannot be grounded in its attached quote."""
from .extractor import _canonical


def quote_contains_value(value: str | None, quote: str | None) -> bool:
    return bool(value and quote and _canonical(value) in _canonical(quote))


def reject_unsupported(findings: dict) -> dict:
    result = {}
    for key, item in findings.items():
        evidence = item.get("evidence") or {}
        if item.get("status") == "verified" and quote_contains_value(item.get("value"), evidence.get("quote")) and evidence.get("source_url"):
            result[key] = item
        else:
            result[key] = {"value": None, "status": "unclear", "evidence": None}
    return result
