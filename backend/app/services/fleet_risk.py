"""
Fleet-wide Risk Heatmap (PRD Section 5.3)
Combines:
1. Physical signal: proportion of CMLs with confidence_low < 2.0 years
   (from rl_predictions — latest computed_at per CML)
2. DM signal: average Active DM matches per equipment per area
   (computed server-side using dm_knowledge_base + equipment attributes,
    matching logic replicated from frontend lib/dm-screener.ts)
"""
from app.core.database import get_db


# ── DM Matching Helpers (port of frontend lib/dm-screener.ts) ────────────────

def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in text.lower().split() if len(t) > 1]


def _match_tokens(dm_keywords: list[str], input_tokens: list[str]) -> bool:
    if not input_tokens:
        return False
    for keyword in dm_keywords:
        kw_tokens = _tokenize(keyword)
        for kt in kw_tokens:
            if kt in input_tokens:
                return True
            for it in input_tokens:
                if kt in it:
                    return True
    return False


# PORT of frontend/src/lib/dm-screener.ts — if DM logic changes in either file,
# MUST update both. See PRD Section 5.3.
def _run_dm_screener(
    equipment: dict,
    dm_knowledge_base: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Replicate runClientSideMatch from frontend.

    Returns (active, possible, related) DM lists.
    """
    mat_tokens = _tokenize(equipment.get("material"))
    fluid_tokens = _tokenize(equipment.get("fluid_service"))
    tmin = equipment.get("design_temp_min") if equipment.get("design_temp_min") is not None else 0
    tmax = equipment.get("design_temp_max") if equipment.get("design_temp_max") is not None else 100
    has_temp = (
        equipment.get("design_temp_min") is not None
        and equipment.get("design_temp_max") is not None
    )

    active: list[dict] = []
    possible: list[dict] = []
    related: list[dict] = []

    for dm in dm_knowledge_base:
        mat_match = _match_tokens(dm.get("materials") or [], mat_tokens)
        fluid_match = _match_tokens(dm.get("fluids") or [], fluid_tokens)
        dm_tmin = dm["temp_min"] if dm.get("temp_min") is not None else -999
        dm_tmax = dm["temp_max"] if dm.get("temp_max") is not None else 999
        temp_match = tmax >= dm_tmin and tmin <= dm_tmax
        score = (1 if mat_match else 0) + (1 if fluid_match else 0) + (1 if temp_match else 0)

        if mat_match and fluid_match and (temp_match or not has_temp):
            active.append(dm)
        elif score >= 2:
            possible.append(dm)
        elif mat_match and fluid_match:
            related.append(dm)

    # PWHT boost (same as frontend)
    pwht = equipment.get("pwht")
    if pwht is False or pwht is None:
        for dm in dm_knowledge_base:
            if dm.get("pwht_flag") != "required":
                continue
            mat_match = _match_tokens(dm.get("materials") or [], mat_tokens)
            fluid_match = _match_tokens(dm.get("fluids") or [], fluid_tokens)
            already_active = any(a["dm_code"] == dm["dm_code"] for a in active)
            already_possible = any(p["dm_code"] == dm["dm_code"] for p in possible)
            if mat_match and fluid_match and not already_active and not already_possible:
                possible.append(dm)

    return active, possible, related


# ── Main compute ──────────────────────────────────────────────────────────────

async def compute(company_id: str, area_id: str = None) -> dict:
    """Compute fleet-wide risk aggregation per area."""
    db = get_db()

    # --- Load reference data ---
    dm_kb = db.table("dm_knowledge_base").select("*").execute()
    dm_kb_data = dm_kb.data or []

    # Build query for areas
    area_query = (
        db.table("plant_areas")
        .select("id, name")
        .eq("company_id", company_id)
    )
    if area_id:
        area_query = area_query.eq("id", area_id)
    areas_result = area_query.execute()
    areas = areas_result.data or []
    area_ids = [a["id"] for a in areas]

    if not area_ids:
        return {"areas": [], "total_areas": 0, "computed_at": None}

    # --- Load equipment per area ---
    equip_result = (
        db.table("equipment")
        .select("id, tag, area_id, material, fluid_service, design_temp_min, design_temp_max, pwht")
        .eq("company_id", company_id)
        .in_("area_id", area_ids)
        .execute()
    )
    equipment_list = equip_result.data or []

    # Group equipment by area
    equip_by_area: dict[str, list[dict]] = {}
    for eq in equipment_list:
        aid = eq.get("area_id")
        if aid:
            equip_by_area.setdefault(aid, []).append(eq)

    # --- Load CMLs + latest RL predictions ---
    cml_result = (
        db.table("cml_points")
        .select("id, equipment_id, location_label, is_active")
        .eq("company_id", company_id)
        .execute()
    )
    cml_list = cml_result.data or []

    # Group CMLs by equipment
    cml_by_equip: dict[str, list[dict]] = {}
    for cml in cml_list:
        eq_id = cml.get("equipment_id")
        if eq_id:
            cml_by_equip.setdefault(eq_id, []).append(cml)

    # Get RL predictions — load ALL for this company
    rl_result = (
        db.table("rl_predictions")
        .select("*")
        .eq("company_id", company_id)
        .execute()
    )
    rl_rows = rl_result.data or []

    # Latest computed_at per CML
    rl_latest: dict[str, dict] = {}
    for row in rl_rows:
        cml_id = row["cml_point_id"]
        existing = rl_latest.get(cml_id)
        if existing is None or row["computed_at"] > existing["computed_at"]:
            rl_latest[cml_id] = row

    # --- Compute per area ---
    area_results = []

    for area in areas:
        aid = area["id"]
        area_equip = equip_by_area.get(aid, [])
        area_cmls: list[dict] = []
        for eq in area_equip:
            area_cmls.extend(cml_by_equip.get(eq["id"], []))

        # --- Physical signal ---
        cmls_with_rl = []
        for cml in area_cmls:
            rl = rl_latest.get(cml["id"])
            if rl is not None:
                cmls_with_rl.append(rl)

        total_cml_with_rl = len(cmls_with_rl)
        low_conf_count = sum(
            1
            for r in cmls_with_rl
            if r.get("confidence_low") is not None and r["confidence_low"] < 2.0
        )
        physical_signal = low_conf_count / total_cml_with_rl if total_cml_with_rl > 0 else 0.0

        # --- DM signal ---
        equip_with_screener = []
        for eq in area_equip:
            # Equipment must have material + fluid to be screenable
            if eq.get("material") and eq.get("fluid_service"):
                equip_with_screener.append(eq)

        total_equip_screened = len(equip_with_screener)

        # DM active count per equipment (total Active matches across all screened equipment)
        total_active_dms = 0
        for eq in equip_with_screener:
            active_dms, _, _ = _run_dm_screener(eq, dm_kb_data)
            total_active_dms += len(active_dms)

        raw_dm_avg = total_active_dms / total_equip_screened if total_equip_screened > 0 else 0.0

        area_results.append({
            "area_id": aid,
            "area_name": area["name"],
            "physical_signal": physical_signal,
            "dm_signal_raw": raw_dm_avg,
            "total_cml_with_rl": total_cml_with_rl,
            "total_equip_screened": total_equip_screened,
            "total_active_dms": total_active_dms,
        })

    # --- Min-max scaling for dm_signal across areas ---
    raw_values = [ar["dm_signal_raw"] for ar in area_results]
    unique_nonzero = {v for v in raw_values if v > 0}

    if len(unique_nonzero) <= 1:
        # No meaningful variation — set all to 0.0
        for ar in area_results:
            ar["dm_signal"] = 0.0
    else:
        mn = min(raw_values)
        mx = max(raw_values)
        for ar in area_results:
            if mx > mn:
                ar["dm_signal"] = (ar["dm_signal_raw"] - mn) / (mx - mn)
            else:
                ar["dm_signal"] = 0.0

    # --- Build output ---
    output_areas = []
    for ar in area_results:
        has_physical_data = ar["total_cml_with_rl"] > 0
        has_dm_data = ar["total_equip_screened"] > 0
        insufficient_data = not has_physical_data and not has_dm_data

        if insufficient_data:
            output_areas.append({
                "area_id": ar["area_id"],
                "area_name": ar["area_name"],
                "physical_signal": 0.0,
                "dm_signal": 0.0,
                "risk_score": None,
                "risk_level": None,
                "insufficient_data": True,
                "cml_count_with_rl": ar["total_cml_with_rl"],
                "equipment_count_with_dm": ar["total_equip_screened"],
            })
            continue

        risk_score = (ar["physical_signal"] * 0.6 + ar["dm_signal"] * 0.4) * 100

        if risk_score >= 50:
            risk_level = "critical"
        elif risk_score >= 30:
            risk_level = "high"
        elif risk_score >= 15:
            risk_level = "medium"
        else:
            risk_level = "low"

        output_areas.append({
            "area_id": ar["area_id"],
            "area_name": ar["area_name"],
            "physical_signal": round(ar["physical_signal"], 4),
            "dm_signal": round(ar["dm_signal"], 4),
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "insufficient_data": False,
            "cml_count_with_rl": ar["total_cml_with_rl"],
            "equipment_count_with_dm": ar["total_equip_screened"],
        })

    # Sort by risk_score descending (nulls last)
    output_areas.sort(
        key=lambda a: (
            0 if a["risk_score"] is None else 1,
            -(a["risk_score"] or 0),
        )
    )

    from datetime import datetime, timezone
    computed_at = datetime.now(timezone.utc).isoformat()

    # Save snapshot
    snapshot_payload = {
        "company_id": company_id,
        "area_id": area_id,
        "risk_summary": {
            "areas": output_areas,
            "total_areas": len(output_areas),
            "computed_at": computed_at,
        },
    }
    db.table("fleet_risk_snapshots").insert(snapshot_payload).execute()

    return {
        "areas": output_areas,
        "total_areas": len(output_areas),
        "computed_at": computed_at,
    }
