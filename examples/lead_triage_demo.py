"""Offline lead-triage demonstration for the Madar AI portfolio.

Uses only Python's standard library. No messages are sent, no external
services are called, and input is never uploaded.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REQUIRED_COLUMNS = {
    "lead_id", "name", "email", "phone", "area", "budget_egp", "property_type", "contact_consent"
}


def _yes(value: str) -> bool:
    return value.strip().casefold() in {"yes", "true", "1"}


def evaluate_lead(row: dict[str, str]) -> dict[str, object]:
    """Validate and classify a single lead. All scoring is rule-based."""
    lead_id = row["lead_id"].strip()
    if not lead_id:
        raise ValueError("missing lead_id")

    email = row["email"].strip().casefold()
    phone = "".join(c for c in row["phone"] if c.isdigit())
    if not email and not phone:
        raise ValueError("email or phone is required")

    raw_budget = row["budget_egp"].strip()
    try:
        budget = int(raw_budget) if raw_budget else 0
    except ValueError as exc:
        raise ValueError("budget_egp must be a non-negative integer") from exc
    if budget < 0:
        raise ValueError("budget_egp must be a non-negative integer")

    area = row["area"].strip()
    property_type = row["property_type"].strip()
    consent = _yes(row["contact_consent"])

    score = (30 if budget else 0) + (20 if area else 0) + (20 if property_type else 0)
    score += (20 if consent else 0) + 10  # a contact method is present
    priority = "high" if score >= 80 else "medium" if score >= 50 else "low"

    # Draft only: a person must review and send it outside this demo.
    draft = None
    if consent:
        first_name = row["name"].strip().split(" ")[0] or "there"
        interest = property_type or "property"
        region = f" in {area}" if area else ""
        draft = (
            f"Hi {first_name}, thanks for your interest in {interest}{region}. "
            "Would you like us to share available options?"
        )

    return {
        "lead_id": lead_id,
        "priority": priority,
        "score": score,
        "next_step": "human_review" if consent else "do_not_contact",
        "draft_for_review": draft,
        "_contact_keys": [key for key in (f"email:{email}" if email else "", f"phone:{phone}" if phone else "") if key],
    }


def process_csv(source: Path) -> dict[str, object]:
    """Return a reviewable summary; never contact customers automatically."""
    processed: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    duplicate_ids: list[str] = []
    seen: set[str] = set()

    with source.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
            raise ValueError(f"Missing CSV columns: {', '.join(missing)}")

        for row_number, row in enumerate(reader, start=2):
            try:
                if any(value is None for value in row.values()):
                    raise ValueError("incomplete CSV row")
                result = evaluate_lead(row)
            except ValueError as exc:
                rejected.append({"row": row_number, "reason": str(exc)})
                continue

            contacts = result.pop("_contact_keys")
            if any(key in seen for key in contacts):
                duplicate_ids.append(str(result["lead_id"]))
                continue
            seen.update(contacts)
            processed.append(result)

    return {
        "mode": "offline_rules_demo",
        "accepted_count": len(processed),
        "duplicates_skipped": duplicate_ids,
        "rejected_rows": rejected,
        "leads_for_review": processed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Madar AI lead-triage demo")
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("sample_leads.csv"))
    parser.add_argument("--output", type=Path, help="Optional JSON output path; treat as private")
    args = parser.parse_args()
    try:
        result = process_csv(args.input)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Demo report saved locally to {args.output}")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
