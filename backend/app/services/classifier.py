"""Supervised page classifier with an explicit keyword fallback."""
from __future__ import annotations

from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[1] / "model_artifacts" / "page_classifier.joblib"
KEYWORDS = ("grievance", "grievance redressal", "complaint officer", "consumer complaints", "nodal officer")


@lru_cache(maxsize=1)
def _load_model():
    if not MODEL_PATH.is_file():
        return None
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def classify_page(title: str, text: str) -> dict:
    haystack = f"{title}\n{text[:20000]}"
    model = _load_model()
    if model is not None:
        probabilities = model.predict_proba([haystack])[0]
        labels = list(model.classes_)
        index = int(probabilities.argmax())
        label = labels[index]
        return {
            "label": "likely_grievance" if label == "grievance" else "unknown",
            "confidence": round(float(probabilities[index]), 3),
            "matched_terms": [],
            "method": "tfidf_logistic_regression",
            "model_available": True,
        }
    folded = haystack.casefold()
    hits = [term for term in KEYWORDS if term in folded]
    return {
        "label": "likely_grievance" if hits else "unknown",
        "confidence": round(len(hits) / len(KEYWORDS), 2),
        "matched_terms": hits,
        "method": "keyword_fallback",
        "model_available": False,
    }


def model_status() -> dict:
    dependencies_available = find_spec("sklearn") is not None and find_spec("joblib") is not None
    artifact_available = MODEL_PATH.is_file()
    return {"page_classifier": "trained" if dependencies_available and artifact_available else "keyword_fallback"}
