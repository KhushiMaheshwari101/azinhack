# Architecture

## Audit

Browser -> FastAPI validates company/domain -> TinyFish Search restricted to the submitted domain -> URL allowlist -> TinyFish Fetch -> TF-IDF/logistic-regression page classifier (keyword fallback) -> regex extraction -> verbatim quote grounding -> explainable checklist -> browser evidence review.

If Fetch yields no grounded fields, TinyFish Agent gets one bounded browser fallback attempt. Agent values are accepted only when the exact value appears in the returned source quote. API keys remain server-side. Demo mode returns labeled synthetic output and makes no provider calls.

## Policy change monitoring

User selects a source URL from the audit UI -> FastAPI verifies the URL is on the submitted domain -> TinyFish Fetch -> SQLite saves a baseline snapshot and normalized text hash. Manual, daily, or weekly checks re-fetch the same URL. Equal normalized hashes create an `unchanged` check; different hashes create a snapshot and change event with old/new excerpts and TF-IDF/logistic-regression category prediction (keyword fallback). The UI surfaces checks, history, and pause controls. Failed fetches are recorded as `failed`, never `unchanged`.

The local scheduler runs in the FastAPI process only when live mode and a TinyFish key are configured. Run one server worker for the hackathon. The deterministic category is a heuristic, not a trained model. The UI should present a content change for human review, not a legal verdict.

The complaint draft remains a deterministic editable template. The demo script and QA command are in `docs/DEMO_RUNBOOK.md`. SQLite and the no-auth API are for local synthetic hackathon use, not production user data.
