from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import get_settings
from .models import AuditRequest, AuditResponse
from .services.classifier import classify_page, model_status
from .services.domain import belongs_to_domain, normalize_domain, require_company_url
from .services.drafter import draft_message
from .services.extractor import extract_fields
from .services.grounding import reject_unsupported
from .services.monitor import (
    MonitorError,
    check_monitor,
    create_monitor,
    run_due_checks,
    create_demo_monitor,
    check_demo_monitor,
)
from .services.scoring import build_checklist
from .services import storage, tinyfish_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("readycheck")
ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


class DraftRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    officer_name: str | None = Field(default=None, max_length=120)
    issue_summary: str = Field(min_length=3, max_length=3000)
    desired_resolution: str = Field(min_length=3, max_length=1000)


class MonitorCreateRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    official_domain: str = Field(min_length=3, max_length=253)
    page_url: str = Field(min_length=8, max_length=2048)
    frequency: Literal["manual", "daily", "weekly"] = "manual"


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_storage()
    settings = get_settings()
    scheduler_task = None
    if settings.scheduler_enabled and not settings.demo_mode and settings.tinyfish_api_key:
        async def scheduler_loop() -> None:
            while True:
                await asyncio.sleep(settings.scheduler_poll_seconds)
                try:
                    await asyncio.to_thread(run_due_checks)
                except Exception:
                    logger.exception("Scheduled monitoring tick failed")
        scheduler_task = asyncio.create_task(scheduler_loop(), name="readycheck-monitor-scheduler")
        logger.info("Policy monitor scheduler enabled; run the hackathon server with one worker.")
    try:
        yield
    finally:
        if scheduler_task:
            scheduler_task.cancel()
            with suppress(asyncio.CancelledError):
                await scheduler_task


app = FastAPI(
    title="ReadyCheck API",
    version="0.2.0",
    description="Evidence-first public grievance page research and change monitoring demo",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


SEEDED_PRESETS = {
    "meesho.com": {
        "company": "Meesho",
        "officer": "A. Grievance Officer",
        "designation": "Grievance Officer (IT Act & E-Commerce Rules)",
        "email": "grievance-officer@meesho.com",
        "phone": "080-61799600",
        "quote": "In accordance with Information Technology Act 2000 and the Consumer Protection (E-Commerce) Rules 2020, the designated Grievance Officer is reachable at grievance-officer@meesho.com (Tel: 080-61799600), Fashnear Technologies.",
        "source": "https://meesho.com/legal/grievance",
        "title": "Meesho Grievance Redressal Mechanism",
    },
    "boat-lifestyle.com": {
        "company": "boAt Lifestyle",
        "officer": "Grievance Redressal Officer",
        "designation": "Nodal Grievance Officer",
        "email": "grievance.officer@imaginemarketingindia.com",
        "phone": "022-69181920",
        "quote": "In accordance with Information Technology Act 2000 and rules made there under, the contact details of the Grievance Officer are: grievance.officer@imaginemarketingindia.com, Phone: 022-69181920.",
        "source": "https://www.boat-lifestyle.com/pages/grievance-redressal",
        "title": "boAt Lifestyle Grievance Policy",
    },
    "nykaa.com": {
        "company": "Nykaa",
        "officer": "Nodal Grievance Team",
        "designation": "Designated Grievance Officer",
        "email": "grievanceofficer@nykaa.com",
        "phone": "1800-267-4444",
        "quote": "For compliance with the Consumer Protection (E-Commerce) Rules, contact the Grievance Officer at grievanceofficer@nykaa.com, Toll-Free: 1800-267-4444, FSN E-Commerce.",
        "source": "https://www.nykaa.com/grievance-officer",
        "title": "Nykaa Grievance Redressal Policy",
    },
}


def demo_response(company: str, domain: str) -> dict:
    matched = None
    for dom_key, preset in SEEDED_PRESETS.items():
        if dom_key in domain or domain in dom_key or preset["company"].lower() in company.lower():
            matched = preset
            break

    if matched:
        source = matched["source"]
        quote = matched["quote"]
        evidence = {"source_url": source, "page_title": matched["title"], "quote": quote}
        fields = {
            "officer_name": {"value": matched["officer"], "status": "verified", "evidence": evidence},
            "designation": {"value": matched["designation"], "status": "verified", "evidence": evidence},
            "email": {"value": matched["email"], "status": "verified", "evidence": evidence},
            "phone": {"value": matched["phone"], "status": "verified", "evidence": evidence},
        }
        classifications = [{"source_url": source, "label": "likely_grievance", "confidence": 0.96, "method": "tfidf_logistic_regression"}]
        return AuditResponse(
            company_name=matched["company"],
            official_domain=domain,
            fields=fields,
            checklist=build_checklist(fields),
            sources_checked=[source],
            page_classifications=classifications,
            demo_mode=True,
        ).model_dump(mode="json")

    # Standard synthetic sample for tests and arbitrary mock audits
    source = f"https://{domain}/grievance-redressal"
    quote = "For assistance, contact our grievance team at care@example.com."
    evidence = {"source_url": source, "page_title": "Synthetic sample page", "quote": quote}
    fields = {
        "officer_name": {"value": None, "status": "unclear", "evidence": None},
        "designation": {"value": "Grievance team", "status": "verified", "evidence": evidence},
        "email": {"value": "care@example.com", "status": "verified", "evidence": evidence},
        "phone": {"value": None, "status": "unclear", "evidence": None},
    }
    return AuditResponse(
        company_name=company,
        official_domain=domain,
        fields=fields,
        checklist=build_checklist(fields),
        sources_checked=[source],
        demo_mode=True,
    ).model_dump(mode="json")


def _require_live() -> None:
    settings = get_settings()
    if settings.demo_mode:
        raise HTTPException(status_code=409, detail="Live monitoring is disabled in demo mode. Set DEMO_MODE=false and configure TINYFISH_API_KEY.")
    if not settings.tinyfish_api_key:
        raise HTTPException(status_code=503, detail="Live mode needs TINYFISH_API_KEY; demo mode makes no provider calls.")


@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "tinyfish_key_configured": bool(settings.tinyfish_api_key),
        "monitoring_available": True,
        "scheduler_enabled": settings.scheduler_enabled and not settings.demo_mode and bool(settings.tinyfish_api_key),
        "database": "sqlite",
        "ml": model_status(),
    }


@app.post("/api/audit")
def audit(request: AuditRequest):
    settings = get_settings()
    domain = normalize_domain(request.official_domain)
    company = request.company_name.strip()
    if settings.demo_mode:
        return demo_response(company, domain)
    if not settings.tinyfish_api_key:
        raise HTTPException(status_code=503, detail="Live mode needs TINYFISH_API_KEY; use demo mode for a free local preview.")
    try:
        candidates = tinyfish_client.search_grievance_pages(company, domain, settings.max_search_results)
        candidates = [item for item in candidates if belongs_to_domain(item.get("url", ""), domain)]
        sources: list[str] = []
        pages: list[dict] = []
        page_classifications: list[dict] = []
        merged: dict = {}
        for item in candidates[:settings.max_search_results]:
            try:
                page = tinyfish_client.fetch_page(item["url"], max_chars=settings.max_page_chars)
                if not page or not page.get("text", "").strip():
                    continue
                final_url = page.get("final_url") or item["url"]
                if not belongs_to_domain(final_url, domain):
                    continue
                page["url"] = final_url
                sources.append(final_url)
                pages.append(page)
            except Exception:
                logger.info("A candidate page could not be fetched; continuing with other candidates.")
        for page in pages:
            prediction = classify_page(page["title"], page["text"])
            page_classifications.append({"source_url": page["url"], **prediction})
            if prediction["label"] == "unknown":
                continue
            grounded = reject_unsupported(extract_fields(page["text"], page["url"], page["title"]))
            for key, finding in grounded.items():
                if finding["status"] == "verified" and merged.get(key, {}).get("status") != "verified":
                    merged[key] = finding
        if not any(value.get("status") == "verified" for value in merged.values()) and candidates:
            candidate_url = candidates[0]["url"]
            try:
                agent = tinyfish_client.agent_fallback(candidate_url, company, settings.max_agent_steps, settings.max_agent_seconds)
            except Exception:
                agent = None
            if agent:
                quote = agent.get("source_quote")
                for key in ("officer_name", "designation", "email", "phone"):
                    value = agent.get(key)
                    if value and quote and str(value).casefold() in str(quote).casefold():
                        merged[key] = {
                            "value": str(value),
                            "status": "verified",
                            "evidence": {"source_url": candidate_url, "page_title": candidates[0].get("title", ""), "quote": str(quote)[:1000]},
                        }
                if quote:
                    sources.append(candidate_url)
        for key in ("officer_name", "designation", "email", "phone"):
            merged.setdefault(key, {"value": None, "status": "unclear", "evidence": None})
        return AuditResponse(
            company_name=company,
            official_domain=domain,
            fields=merged,
            checklist=build_checklist(merged),
            sources_checked=list(dict.fromkeys(sources)),
            page_classifications=page_classifications,
            demo_mode=False,
        ).model_dump(mode="json")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Live audit provider call failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Live web research failed. Check provider settings and retry, or use demo mode.") from exc


@app.post("/api/monitor", status_code=201)
def add_monitor(request: MonitorCreateRequest):
    settings = get_settings()
    if storage.active_monitor_count() >= settings.max_monitored_pages:
        raise HTTPException(status_code=429, detail="The local monitor limit has been reached. Pause a page before adding another.")
    domain = normalize_domain(request.official_domain)
    page_url = request.page_url.strip()
    require_company_url(page_url, domain)
    try:
        if settings.demo_mode or not settings.tinyfish_api_key:
            return create_demo_monitor(
                company_name=request.company_name.strip(),
                domain=domain,
                page_url=page_url,
                frequency=request.frequency,
            )
        return create_monitor(
            company_name=request.company_name.strip(),
            domain=domain,
            page_url=page_url,
            frequency=request.frequency,
        )
    except MonitorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Could not create policy monitor (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Could not save a baseline for this page. Check the URL and retry.") from exc


@app.get("/api/monitor")
def list_monitors():
    storage.init_storage()
    return {"monitors": storage.list_monitors()}


@app.post("/api/monitor/{monitor_id}/check")
def run_monitor_check(monitor_id: str):
    settings = get_settings()
    try:
        if settings.demo_mode or not settings.tinyfish_api_key:
            return check_demo_monitor(monitor_id)
        return check_monitor(monitor_id)
    except MonitorError as exc:
        if exc.code == "not_found":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if exc.code == "inactive":
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        storage.record_failed_check(monitor_id, exc.code)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Manual policy page check failed (%s)", type(exc).__name__)
        storage.record_failed_check(monitor_id, "provider_error")
        raise HTTPException(status_code=502, detail="Page check failed. The previous snapshot was kept; retry later.") from exc


@app.get("/api/monitor/{monitor_id}/history")
def get_monitor_history(monitor_id: str):
    storage.init_storage()
    result = storage.monitor_history(monitor_id)
    if not result:
        raise HTTPException(status_code=404, detail="This monitored page was not found.")
    return result


@app.post("/api/monitor/{monitor_id}/pause")
def stop_monitor(monitor_id: str):
    if not storage.deactivate_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="This monitored page was not found.")
    return {"monitor_id": monitor_id, "active": False, "history_preserved": True}


@app.post("/api/draft")
def create_draft(request: DraftRequest):
    return {"draft": draft_message(request.company_name.strip(), request.officer_name, request.issue_summary, request.desired_resolution)}
