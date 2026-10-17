"""Classify policy-page diffs using a trained model or transparent rules."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[1] / "model_artifacts" / "change_classifier.joblib"
CATEGORIES = ("contact_details", "officer_details", "response_timeline", "complaint_process", "other_content")


@lru_cache(maxsize=1)
def _load_model():
    if not MODEL_PATH.is_file():
        return None
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def classify_change(old_excerpt: str, new_excerpt: str) -> dict:
    sample = f"Previous policy text: {old_excerpt}\nUpdated policy text: {new_excerpt}"
    model = _load_model()
    if model is not None:
        probabilities = model.predict_proba([sample])[0]
        index = int(probabilities.argmax())
        return {"category": str(model.classes_[index]), "confidence": round(float(probabilities[index]), 3), "method": "tfidf_logistic_regression"}
    combined = sample.casefold()
    rules = [
        ("contact_details", ("email", "@", "phone", "telephone", "mobile", "contact number", "helpline")),
        ("officer_details", ("grievance officer", "officer name", "nodal officer", "designation")),
        ("response_timeline", ("hours", "days", "weeks", "month", "within", "acknowledge", "redress")),
        ("complaint_process", ("complaint", "grievance", "refund", "return", "escalat", "resolution")),
    ]
    category = next((name for name, terms in rules if any(term in combined for term in terms)), "other_content")
    return {"category": category, "confidence": 0.0, "method": "keyword_fallback"}
