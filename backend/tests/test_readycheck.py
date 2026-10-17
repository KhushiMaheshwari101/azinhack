"""Local integration checks for the ReadyCheck demo and evidence pipeline."""
from __future__ import annotations

import unittest

from fastapi import HTTPException

from backend.app.services.classifier import classify_page, model_status
from backend.app.services.domain import belongs_to_domain, normalize_domain
from backend.app.services.extractor import extract_fields
from backend.app.services.grounding import reject_unsupported
from backend.app.services.monitor import compare_text


class DomainSafetyTests(unittest.TestCase):
    def test_normalizes_url_to_public_domain(self):
        self.assertEqual(normalize_domain("https://Shop.Example.com/path"), "shop.example.com")

    def test_rejects_local_ip_domains(self):
        with self.assertRaises(HTTPException):
            normalize_domain("127.0.0.1")

    def test_domain_match_rejects_lookalike_suffix(self):
        self.assertTrue(belongs_to_domain("https://support.example.com/policy", "example.com"))
        self.assertFalse(belongs_to_domain("https://example.com.attacker.test/page", "example.com"))


class EvidencePipelineTests(unittest.TestCase):
    def test_extractor_preserves_obfuscated_email_quote_and_grounding(self):
        text = "Grievance Officer: Asha Rao\nEmail: care [at] example [dot] com\nPhone: 1800-222-3333"
        findings = extract_fields(text, "https://example.com/grievance", "Grievance")
        grounded = reject_unsupported(findings)
        self.assertEqual(grounded["email"]["status"], "verified")
        self.assertIn("[at]", grounded["email"]["evidence"]["quote"])
        self.assertEqual(grounded["officer_name"]["value"], "Asha Rao")
        self.assertEqual(grounded["phone"]["status"], "verified")

    def test_grounding_rejects_a_value_not_in_its_quote(self):
        value = {"email": {"value": "fake@example.com", "status": "verified", "evidence": {"source_url": "https://example.com", "quote": "No contact details here."}}}
        result = reject_unsupported(value)
        self.assertEqual(result["email"]["status"], "unclear")
        self.assertIsNone(result["email"]["value"])

    def test_page_classifier_returns_valid_prediction_and_provenance(self):
        result = classify_page("Grievance Redressal", "Contact the grievance officer for complaint support.")
        self.assertEqual(result["label"], "likely_grievance")
        self.assertIn(result["method"], {"tfidf_logistic_regression", "keyword_fallback"})
        self.assertIn("page_classifier", model_status())

    def test_policy_diff_detects_contact_change(self):
        unchanged = compare_text("Email: help@example.com", "Email: help@example.com")
        changed = compare_text("Email: help@example.com", "Email: grievance@example.com")
        self.assertFalse(unchanged["changed"])
        self.assertTrue(changed["changed"])
        self.assertIn(changed["category"], {"contact_details", "officer_details", "response_timeline", "complaint_process", "other_content"})
        self.assertIn(changed["category_method"], {"tfidf_logistic_regression", "keyword_fallback"})


class DemoContractTests(unittest.TestCase):
    def test_demo_response_is_explicitly_synthetic_and_grounded(self):
        from backend.app.main import demo_response

        response = demo_response("Sample Store", "example.com")
        self.assertTrue(response["demo_mode"])
        self.assertIn("Synthetic", response["fields"]["email"]["evidence"]["page_title"])
        self.assertIn(response["fields"]["email"]["value"], response["fields"]["email"]["evidence"]["quote"])


if __name__ == "__main__":
    unittest.main()
