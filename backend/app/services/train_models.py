"""Train reproducible TF-IDF + logistic regression models from labeled JSONL fixtures.

Run from the repository root: python -m backend.app.services.train_models
The fixtures included in this project are synthetic and do not establish real-world accuracy.
"""
from __future__ import annotations

import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "data" / "fixtures"
ARTIFACTS = Path(__file__).resolve().parents[1] / "model_artifacts"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def train(name: str, path: Path, text_key: str, label_key: str) -> dict:
    rows = read_jsonl(path)
    texts = [row[text_key] for row in rows]
    labels = [row[label_key] for row in rows]
    if len(set(labels)) < 2 or min(labels.count(label) for label in set(labels)) < 2:
        raise ValueError(f"{path.name} needs at least two examples per class")
    x_train, x_valid, y_train, y_valid = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels,
    )
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, strip_accents="unicode", sublinear_tf=True)),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])
    model.fit(x_train, y_train)
    report = classification_report(y_valid, model.predict(x_valid), output_dict=True, zero_division=0)
    import joblib
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS / f"{name}.joblib")
    summary = {
        "model": name,
        "algorithm": "TF-IDF word uni/bigrams + logistic regression",
        "fixture_count": len(rows),
        "synthetic_examples": sum(bool(row.get("synthetic", False)) for row in rows),
        "validation_count": len(y_valid),
        "validation_split": "stratified 75/25; random_state=42",
        "validation_report": report,
        "limitation": "Synthetic prototype fixtures only; not evidence of real-world accuracy.",
    }
    return summary


def main() -> None:
    summaries = [
        train("page_classifier", FIXTURES / "page_classification.jsonl", "text", "label"),
        train("change_classifier", FIXTURES / "change_categories.jsonl", "text", "label"),
    ]
    report_path = ARTIFACTS / "training_report.json"
    report_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(json.dumps(summaries, indent=2))
    print(f"Saved model artifacts and validation report under {ARTIFACTS}")


if __name__ == "__main__":
    main()
