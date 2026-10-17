"""Domain and URL checks used before sending a page to TinyFish."""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from fastapi import HTTPException

DOMAIN_RE = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", re.I)


def normalize_domain(value: str) -> str:
    raw = (value or "").strip()
    if not raw or len(raw) > 2048:
        raise HTTPException(status_code=422, detail="Enter a valid company domain, such as example.com.")
    candidate = raw if "://" in raw else f"//{raw}"
    try:
        parsed = urlsplit(candidate)
        host = (parsed.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
        port = parsed.port
    except (ValueError, UnicodeError):
        raise HTTPException(status_code=422, detail="Enter a valid company domain, such as example.com.")
    if parsed.username or parsed.password or port not in (None, 80, 443):
        raise HTTPException(status_code=422, detail="Use a public company domain without credentials or a custom port.")
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    if is_ip or host in {"localhost", "localhost.localdomain"} or not DOMAIN_RE.fullmatch(host):
        raise HTTPException(status_code=422, detail="Enter a public company domain, such as example.com.")
    return host


def belongs_to_domain(url: str, domain: str) -> bool:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
        port = parsed.port
    except (ValueError, UnicodeError):
        return False
    if parsed.scheme.lower() not in {"http", "https"} or parsed.username or parsed.password:
        return False
    if port not in (None, 80, 443):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    normalized = domain.rstrip(".").lower()
    return bool(host) and (host == normalized or host.endswith("." + normalized))


def require_company_url(url: str, domain: str) -> str:
    if not belongs_to_domain(url, domain):
        raise HTTPException(status_code=422, detail="The page URL must use the submitted company domain.")
    return url
