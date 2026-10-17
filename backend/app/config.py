from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class Settings:
    demo_mode: bool
    tinyfish_api_key: str
    max_search_results: int
    max_agent_steps: int
    max_agent_seconds: int
    max_page_chars: int
    max_monitored_pages: int
    database_path: Path
    scheduler_enabled: bool
    scheduler_poll_seconds: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    demo_mode = os.getenv("DEMO_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
    scheduler_enabled = os.getenv("ENABLE_MONITOR_SCHEDULER", "true").strip().lower() in {"1", "true", "yes", "on"}
    database_path = Path(os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "data" / "readycheck.sqlite3"))).expanduser()
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path
    return Settings(
        demo_mode=demo_mode,
        tinyfish_api_key=os.getenv("TINYFISH_API_KEY", "").strip(),
        max_search_results=_bounded_int("MAX_SEARCH_RESULTS", 5, 1, 10),
        max_agent_steps=_bounded_int("MAX_AGENT_STEPS", 8, 1, 20),
        max_agent_seconds=_bounded_int("MAX_AGENT_SECONDS", 45, 1, 90),
        max_page_chars=_bounded_int("MAX_PAGE_CHARS", 120_000, 5_000, 500_000),
        max_monitored_pages=_bounded_int("MAX_MONITORED_PAGES", 50, 1, 500),
        database_path=database_path,
        scheduler_enabled=scheduler_enabled,
        scheduler_poll_seconds=_bounded_int("SCHEDULER_POLL_SECONDS", 60, 15, 3600),
    )
