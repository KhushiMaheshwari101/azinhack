from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl
Status = Literal["verified", "not_found", "unclear"]
class AuditRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    official_domain: str = Field(min_length=3, max_length=253)
class Evidence(BaseModel):
    source_url: HttpUrl
    page_title: str = ""
    quote: str = Field(min_length=1)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
class FieldFinding(BaseModel):
    value: str | None = None
    status: Status = "unclear"
    evidence: Evidence | None = None
class ChecklistItem(BaseModel):
    label: str
    status: Status
    explanation: str
    evidence: Evidence | None = None
class AuditResponse(BaseModel):
    company_name: str
    official_domain: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fields: dict[str, FieldFinding]
    checklist: list[ChecklistItem]
    sources_checked: list[str] = []
    page_classifications: list[dict] = []
    demo_mode: bool = False
    disclaimer: str = "Research aid only. Verify sources manually; not legal advice or a compliance certification."
