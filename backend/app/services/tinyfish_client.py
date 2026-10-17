"""Small, server-only TinyFish SDK adapter. Search and Fetch precede Agent."""
from __future__ import annotations

from typing import Any

from tinyfish import TinyFish
from tinyfish.agent.types import AgentConfig

from ..config import get_settings


def _client(timeout: float = 35) -> TinyFish:
    key = get_settings().tinyfish_api_key
    if not key:
        raise RuntimeError("TinyFish is not configured")
    return TinyFish(api_key=key, timeout=timeout, max_retries=1)


def search_grievance_pages(company_name: str, domain: str, limit: int = 5) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 10))
    response = _client().search.query(
        query=f"{company_name} grievance officer grievance redressal contact policy",
        purpose="Find the company's public grievance, contact, or policy page.",
        include_domains=domain,
        page=0,
    )
    return [
        {"url": item.url, "title": item.title or "", "snippet": item.snippet or "", "site_name": item.site_name or ""}
        for item in response.results[:limit]
    ]


def fetch_page(
    url: str,
    max_chars: int | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
) -> dict[str, Any] | None:
    response = _client().fetch.get_contents(
        urls=[url],
        purpose="Retrieve public grievance or policy text for evidence review and change monitoring.",
        format="markdown",
        links=True,
        per_url_timeout_ms=30_000,
        ttl=0,
        if_none_match=etag,
        if_modified_since=last_modified,
        include_etag_and_last_modified=True,
    )
    if not response.results:
        return None
    item = response.results[0]
    text = (item.text or "").strip()
    if max_chars is not None:
        text = text[:max_chars]
    return {
        "url": item.url,
        "final_url": item.final_url or item.url,
        "title": item.title or "",
        "text": text,
        "links": item.links or [],
        "etag": item.etag,
        "last_modified": item.last_modified,
        "not_modified": item.not_modified,
        "latency_ms": item.latency_ms,
    }


def agent_fallback(url: str, company_name: str, max_steps: int = 8, max_seconds: int = 45) -> dict[str, Any] | None:
    schema = {
        "type": "object",
        "properties": {
            "officer_name": {"type": ["string", "null"]},
            "designation": {"type": ["string", "null"]},
            "email": {"type": ["string", "null"]},
            "phone": {"type": ["string", "null"]},
            "source_quote": {"type": ["string", "null"]},
        },
        "required": ["officer_name", "designation", "email", "phone", "source_quote"],
        "additionalProperties": False,
    }
    final: dict[str, Any] | None = None
    with _client(timeout=min(max(max_seconds + 10, 35), 105)).agent.stream(
        url=url,
        goal=(f"Find visible public grievance officer information for {company_name}. "
              "Return only text visible on this page and an exact supporting quote. Do not infer."),
        agent_config=AgentConfig(max_steps=max_steps, max_duration_seconds=max_seconds),
        output_schema=schema,
    ) as stream:
        for event in stream:
            if str(getattr(event, "type", "")) == "COMPLETE":
                if getattr(event, "status", "") == "COMPLETED":
                    value = getattr(event, "result_json", None)
                    final = value if isinstance(value, dict) else None
    return final
