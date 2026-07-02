"""
DM Accuracy Validation — PRD Section 5.4
==========================================
Compares predicted DM codes (from DM Screener) with actual field findings
recorded in checklist_answers notes. Computes match_score per equipment.

Reuses _run_dm_screener from fleet_risk.py
See PRD Section 5.3 and 5.4
"""

import re, math
from app.core.database import get_db
from app.services.fleet_risk import _run_dm_screener, _tokenize


STOPWORDS = {
    "corrosion", "high", "low", "temperature", "stress",
    "damage", "attack", "cracking", "induced", "and", "of",
    "the", "in", "at", "with", "for", "under", "including",
    "assisted", "related", "enhanced",
}


def _extract_dm_keyword(dm_name: str) -> str:
    """Extract a single distinctive keyword from DM name.

    Priority:
    1. Short parenthesized text (≤15 chars, not Including/Excluding/Also)
    2. Fallback: first distinctive word after removing stopwords
    """
    # Step a: parenthesized text
    m = re.search(r'\(([^)]+)\)', dm_name)
    if m:
        text = m.group(1).strip()
        if (
            len(text) <= 15
            and not text.startswith("Including")
            and not text.startswith("Excluding")
            and not text.startswith("Also")
        ):
            return text

    # Step c: fallback — split, remove stopwords
    words = re.split(r"[\s/]+", dm_name)
    distinctive = [w for w in words if w.lower() not in STOPWORDS and len(w) > 1]

    if distinctive:
        # Return 1-2 words
        return distinctive[0] if len(distinctive) == 1 else f"{distinctive[0]} {distinctive[1]}"

    # Absolute fallback: first word
    return words[0] if words else dm_name


def _collect_notes(equipment_id: str) -> str:
    """Collect all checklist notes for an equipment from inspection events."""
    db = get_db()

    # Get all inspection events for this equipment
    events = (
        db.table("inspection_events")
        .select("id")
        .eq("equipment_id", equipment_id)
        .execute()
    )
    if not events.data:
        return ""

    event_ids = [ev["id"] for ev in events.data]

    # Fetch notes in batches of 50 (supabase REST limit)
    corpus_parts = []
    for i in range(0, len(event_ids), 50):
        batch = event_ids[i : i + 50]
        notes_rows = (
            db.table("checklist_answers")
            .select("notes")
            .in_("inspection_event_id", batch)
            .execute()
        )
        for row in notes_rows.data:
            note = (row.get("notes") or "").strip()
            if note:
                corpus_parts.append(note)

    return " ".join(corpus_parts)


async def compute(company_id: str) -> dict:
    """Compute DM accuracy validation for all equipment in a company.

    For each equipment:
      - Run DM Screener to get predicted Active DM codes
      - Compare against keywords in field notes (checklist_answers)
      - Compute match_score = found / predicted

    Returns full result with per-equipment breakdown.
    """
    db = get_db()

    # All equipment for this company
    equip_list = (
        db.table("equipment")
        .select("id, tag, material, fluid_service, design_temp_min, design_temp_max, pwht")
        .eq("company_id", company_id)
        .execute()
    )
    if not equip_list.data:
        return {"company_id": company_id, "total_equipment_screened": 0, "total_with_active_dm": 0, "total_validated": 0, "results": [], "computed_at": None}

    # Load dm_knowledge_base once
    dm_kb = db.table("dm_knowledge_base").select("*").execute().data

    results = []
    total_with_active_dm = 0
    total_validated = 0

    for eq in equip_list.data:
        # Run DM Screener
        active_dms, possible_dms, related_dms = _run_dm_screener(eq, dm_kb)

        if not active_dms:
            # Skip equipment with no active DMs
            continue

        total_with_active_dm += 1

        # Collect notes
        notes_corpus = _collect_notes(eq["id"])
        notes_lower = notes_corpus.lower()

        # Match each active DM against notes
        predicted_codes = [dm["dm_code"] for dm in active_dms]
        actual_codes = []

        for dm in active_dms:
            keyword = _extract_dm_keyword(dm["dm_name"])
            if keyword.lower() in notes_lower:
                actual_codes.append(dm["dm_code"])

        # Calculate match score
        match_score = round(len(actual_codes) / len(predicted_codes), 4) if predicted_codes else 0.0

        # Save to dm_validation_results
        db.table("dm_validation_results").insert(
            {
                "company_id": company_id,
                "equipment_id": eq["id"],
                "predicted_dm_codes": predicted_codes,
                "actual_finding_dm_codes": actual_codes,
                "match_score": match_score if notes_corpus else 0.0,
            }
        ).execute()

        total_validated += 1

        # Build result entry
        match_pct = f"{int(round(match_score * 100))}%"
        results.append(
            {
                "equipment_id": eq["id"],
                "equipment_tag": eq["tag"],
                "predicted_dm_codes": predicted_codes,
                "actual_finding_dm_codes": actual_codes,
                "match_score": match_score,
                "match_percentage": match_pct,
            }
        )

    # Sort by match_score descending
    results.sort(key=lambda r: r["match_score"], reverse=True)

    # Get computed_at from the last inserted row
    last_row = (
        db.table("dm_validation_results")
        .select("computed_at")
        .eq("company_id", company_id)
        .order("computed_at", desc=True)
        .limit(1)
        .execute()
    )
    computed_at = last_row.data[0]["computed_at"] if last_row.data else None

    return {
        "company_id": company_id,
        "total_equipment_screened": len(equip_list.data),
        "total_with_active_dm": total_with_active_dm,
        "total_validated": total_validated,
        "results": results,
        "computed_at": str(computed_at) if computed_at else None,
    }
