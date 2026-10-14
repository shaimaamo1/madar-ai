"""Unit tests for the offline Madar lead-triage example."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from lead_triage_demo import evaluate_lead, process_csv  # noqa: E402


class LeadTriageTests(unittest.TestCase):
    def setUp(self):
        self.lead = {
            "lead_id": "L1", "name": "Nour", "email": "nour@example.com", "phone": "01000000001",
            "area": "New Cairo", "budget_egp": "3500000", "property_type": "Apartment",
            "contact_consent": "yes",
        }

    def test_high_priority_and_human_review(self):
        result = evaluate_lead(self.lead)
        self.assertEqual(result["priority"], "high")
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["next_step"], "human_review")
        self.assertIn("Hi Nour", result["draft_for_review"])

    def test_no_consent_means_no_draft(self):
        self.lead["contact_consent"] = "no"
        result = evaluate_lead(self.lead)
        self.assertEqual(result["next_step"], "do_not_contact")
        self.assertIsNone(result["draft_for_review"])

    def test_negative_budget_rejected(self):
        self.lead["budget_egp"] = "-10"
        with self.assertRaisesRegex(ValueError, "non-negative"):
            evaluate_lead(self.lead)

    def test_duplicate_and_invalid_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "leads.csv"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.lead.keys())
                writer.writeheader()
                writer.writerow(self.lead)
                writer.writerow({**self.lead, "lead_id": "L2", "email": "new@example.com"})
                writer.writerow({**self.lead, "lead_id": "L3", "email": "other@example.com", "phone": "0109", "budget_egp": "oops"})
            report = process_csv(source)
            self.assertEqual(report["accepted_count"], 1)
            self.assertEqual(report["duplicates_skipped"], ["L2"])
            self.assertEqual(len(report["rejected_rows"]), 1)

    def test_missing_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "leads.csv"
            source.write_text("lead_id,name\n1,Nour\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing CSV columns"):
                process_csv(source)


if __name__ == "__main__":
    unittest.main()
