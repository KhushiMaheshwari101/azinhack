# ML workflow and evaluation

ReadyCheck has two supervised prototypes: grievance-page classification (`grievance` / `other`) and policy-change categorization (`contact_details`, `officer_details`, `response_timeline`, `complaint_process`, `other_content`). Both use a scikit-learn pipeline with word TF-IDF uni/bigrams and logistic regression. If a model artifact is missing/unreadable, runtime uses the documented keyword fallback.

## Train or retrain

From the repository root, with `requirements.txt` installed:

```powershell
python -m backend.app.services.train_models
```

This reads `data/fixtures/page_classification.jsonl` and `data/fixtures/change_categories.jsonl`, uses a stratified 75/25 holdout split with `random_state=42`, and writes two `.joblib` models plus `backend/app/model_artifacts/training_report.json`. `/api/health` reports whether page classification is using the trained model or fallback. Audit responses include each candidate page's prediction, confidence, method, and URL. Monitor change events use the change classifier.

## Dataset and limits

The checked-in examples are synthetic teaching fixtures, not collected or manually reviewed company pages. The generated holdout metrics are therefore only a pipeline smoke measure on synthetic data; they must not be presented as expected real-world performance. The small dataset is not enough to establish generalization, especially across languages, site templates, OCR, or unusual policy wording. Use a manually reviewed, source-linked set of real public pages and diffs before making quality claims.

When collecting real evaluation examples, record a stable case ID, public source URL, label, short necessary quote, reviewer, review date, and split. Keep all examples from one company/domain in only one split to reduce leakage. Report class support and precision/recall/F1 per class, macro-F1, confusion matrix, field-level precision/recall, grounded-field rate, false-verified rate, correct-unclear rate, latency, provider steps, and cost. Never put secrets or unnecessary personal data in fixtures.

## Evidence safety

The classifier only prioritizes pages; it does not establish compliance. Extraction returns conservative regex candidates. `grounding.reject_unsupported` rejects a verified value unless it appears in its attached quote and a source URL is present. Keep the verbatim quote and source URL with every accepted field, manually review before relying on results, and never convert classifier confidence into a legal or compliance conclusion.
