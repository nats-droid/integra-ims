"""
Remaining Life Calculator — Circuit-Level Aggregation
======================================================
Approach:
1. Per CML point: linear regression on thickness_readings → corrosion rate
2. Per circuit: take MIN remaining life across its CML points
3. Per equipment: take MIN across circuits
4. Result → inspection_plans.remaining_life_date (CAPPED at 30y for planning)

Equipment eligibility:
  - Eligible (thickness-based RL): piping, vessel, tank, heater
  - Excluded (non-thickness): pump, compressor (rotating)
  - Excluded (non-thickness): psv (API 576 — set pressure test)
  - Excluded (specific tag): EX-301 (misclassified as 'other')
  - 'other' type: eligible but flagged for manual review
"""

import numpy as np
from datetime import date, datetime, timedelta
from typing import Optional
from app.core.database import get_db
from supabase import Client


# Equipment types eligible for thickness-based remaining life calculation
# Others (pump, compressor, psv) use different assessment methods
RL_ELIGIBLE_TYPES = ('piping', 'vessel', 'tank', 'heater', 'other')

# Specific equipment tags excluded from thickness RL
RL_EXCLUDED_TAGS = ('EX-301',)

# CAP for inspection_plan: max 30 years (practical planning horizon)
# Raw values stored separately in rl_predictions
RL_CAP_YEARS = 30


def calc_corrosion_rate(readings: list) -> float:
    """Linear regression: reading_mm ~ reading_date → corrosion rate in mm/year."""
    if len(readings) < 2:
        return 0.0
    try:
        base = datetime.fromisoformat(readings[0]["reading_date"]).toordinal()
        dates = np.array([
            datetime.fromisoformat(r["reading_date"]).toordinal() - base
            for r in readings
        ], dtype=float)
        thickness = np.array([r["reading_mm"] for r in readings], dtype=float)
        m, _ = np.polyfit(dates, thickness, 1)
        rate = -m * 365.0
        return max(rate, 0.0)
    except Exception:
        return 0.0


def calc_cml_remaining_life(cml: dict, readings: list, governing_cr_cache: Optional[float]) -> Optional[float]:
    """Calculate remaining life in years for one CML point."""
    if len(readings) < 2:
        return None
    t_min = cml.get("t_min")
    if t_min is None:
        t_min = cml.get("nominal_thickness", 10) * cml.get("retirement_factor", 0.875)
    latest = readings[-1]["reading_mm"]
    remaining = latest - t_min
    if remaining <= 0:
        return 0.0
    rate = governing_cr_cache if (governing_cr_cache and governing_cr_cache > 0) else calc_corrosion_rate(readings)
    if rate <= 0:
        return 50.0
    return remaining / rate


def calculate_for_equipment(db: Client, equipment_id: str, company_id: str) -> dict:
    """Calculate remaining life for all circuits of one equipment.
    Returns summary with capped remaining_life_date + raw per-CML predictions."""
    circuits = db.table("circuits") \
        .select("id, name, governing_cr_cache") \
        .eq("equipment_id", equipment_id) \
        .eq("company_id", company_id) \
        .execute()
    if not circuits.data:
        return {"equipment_id": equipment_id, "status": "no_circuits"}
    circuit_rl_years = []
    errors = []
    cml_predictions = []  # raw per-CML for rl_predictions table
    for circuit in circuits.data:
        cmls = db.table("cml_points") \
            .select("id, location_label, t_min, nominal_thickness, retirement_factor") \
            .eq("circuit_id", circuit["id"]) \
            .eq("company_id", company_id) \
            .execute()
        if not cmls.data:
            continue
        cml_rl_years = []
        for cml in cmls.data:
            readings = db.table("thickness_readings") \
                .select("reading_date, reading_mm") \
                .eq("cml_point_id", cml["id"]) \
                .eq("company_id", company_id) \
                .order("reading_date") \
                .execute()
            rl = calc_cml_remaining_life(cml, readings.data, circuit.get("governing_cr_cache"))
            if rl is not None:
                cml_rl_years.append(rl)
                cml_predictions.append({
                    "cml_point_id": cml["id"],
                    "predicted_rl_years": round(rl, 2),
                    "confidence_high": None,
                    "confidence_low": None,
                })
            else:
                errors.append({"circuit": circuit["name"], "cml": cml["location_label"], "reason": "insufficient_readings"})
        if cml_rl_years:
            circuit_rl_years.append(min(cml_rl_years))
    if not circuit_rl_years:
        return {"equipment_id": equipment_id, "status": "no_data", "errors": errors}
    equipment_rl_years = min(circuit_rl_years)
    # Apply CAP
    capped_years = min(equipment_rl_years, RL_CAP_YEARS)
    rl_date = date.today() + timedelta(days=int(capped_years * 365))
    return {
        "equipment_id": equipment_id,
        "remaining_life_years": round(equipment_rl_years, 2),
        "remaining_life_date": rl_date.isoformat(),
        "capped": True if equipment_rl_years > RL_CAP_YEARS else False,
        "n_circuits": len(circuit_rl_years),
        "errors": errors,
        "status": "success",
        "equipment_type": None,
        "cml_predictions": cml_predictions,
    }


async def batch_recalculate(
    db: Client,
    company_id: str,
    equipment_ids: Optional[list[str]] = None,
) -> dict:
    """Recalculate remaining life for all eligible equipment.
    PSV: creates plan with NULL remaining_life_date (disnaker_date primary).
    """
    query = db.table("equipment") \
        .select("id, tag, type, company_id") \
        .eq("company_id", company_id) \
        .eq("is_active", True)
    if equipment_ids:
        query = query.in_("id", equipment_ids)
    equipment_list = query.execute()
    if not equipment_list.data:
        return {"updated": 0, "errors": [], "skipped": []}
    updated = 0
    all_errors = []
    skipped = []
    for eq in equipment_list.data:
        eq_type = eq["type"]
        eq_tag = eq["tag"]
        if eq_type == 'psv':
            existing = db.table("inspection_plans") \
                .select("id, approval_status") \
                .eq("equipment_id", eq["id"]) \
                .eq("company_id", company_id) \
                .execute()
            if not existing.data:
                db.table("inspection_plans").insert({
                    "company_id": company_id,
                    "equipment_id": eq["id"],
                    "inspection_type": "external",
                    "remaining_life_date": None,
                }).execute()
                skipped.append({"equipment_id": eq["id"], "tag": eq_tag, "type": eq_type, "reason": "psv — no RL, plan with NULL"})
            else:
                skipped.append({"equipment_id": eq["id"], "tag": eq_tag, "type": eq_type, "reason": "psv — plan exists"})
            continue
        if eq_type not in RL_ELIGIBLE_TYPES:
            skipped.append({"equipment_id": eq["id"], "tag": eq_tag, "type": eq_type, "reason": f"type '{eq_type}' not eligible"})
            continue
        if eq_tag in RL_EXCLUDED_TAGS:
            skipped.append({"equipment_id": eq["id"], "tag": eq_tag, "type": eq_type, "reason": "excluded tag"})
            continue
        result = calculate_for_equipment(db, eq["id"], company_id)
        result["equipment_type"] = eq_type
        # Flag 'other' type for manual review (not explicitly thickness-driven)
        if eq_type == "other":
            result["manual_review"] = True
        else:
            result["manual_review"] = False
        if result.get("status") != "success":
            if result.get("errors"):
                all_errors.extend(result["errors"])
            skipped.append(result)
            continue
        
        # Write raw per-CML predictions to rl_predictions (uncapped, analytical)
        cml_predictions = result.get("cml_predictions", [])
        for pred in cml_predictions:
            pred["company_id"] = company_id
            existing_pred = db.table("rl_predictions") \
                .select("id") \
                .eq("cml_point_id", pred["cml_point_id"]) \
                .eq("company_id", company_id) \
                .execute()
            if existing_pred.data:
                db.table("rl_predictions") \
                    .update({"predicted_rl_years": pred["predicted_rl_years"]}) \
                    .eq("id", existing_pred.data[0]["id"]) \
                    .execute()
            else:
                db.table("rl_predictions").insert(pred).execute()
        
        existing = db.table("inspection_plans") \
            .select("id, approval_status") \
            .eq("equipment_id", eq["id"]) \
            .eq("company_id", company_id) \
            .execute()
        plan_data = {
            "company_id": company_id,
            "equipment_id": eq["id"],
            "inspection_type": "external",
            "remaining_life_date": result["remaining_life_date"],
        }
        if existing.data:
            plan = existing.data[0]
            if plan["approval_status"] in ("pending", None, "revised"):
                db.table("inspection_plans") \
                    .update({"remaining_life_date": result["remaining_life_date"]}) \
                    .eq("id", plan["id"]) \
                    .execute()
                updated += 1
        else:
            db.table("inspection_plans").insert(plan_data).execute()
            updated += 1
    return {
        "updated": updated,
        "total_equipment": len(equipment_list.data),
        "skipped": skipped,
        "errors": all_errors,
    }