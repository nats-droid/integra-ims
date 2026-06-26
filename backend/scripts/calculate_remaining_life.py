#!/usr/bin/env python3
"""
Batch Remaining Life Calculator — Standalone Script
====================================================
Initial population of inspection_plans.remaining_life_date for all eligible equipment.

Eligibility:
  ✅ piping, vessel, tank, heater: full RL calculation
  ✅ 'other': calculated but flagged for manual review
  ❌ pump, compressor: rotating equipment, no thickness RL
  ❌ psv: API 576 (set pressure test), not thickness-driven
  ❌ EX-301: misclassified, excluded by specific tag

Usage:
  source venv/bin/activate
  python scripts/calculate_remaining_life.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
import numpy as np
from datetime import date, datetime, timedelta
from typing import Optional

URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not URL or not SERVICE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

sb = create_client(URL, SERVICE_KEY)

# Equipment types eligible for thickness-based RL
RL_ELIGIBLE_TYPES = ('piping', 'vessel', 'tank', 'heater', 'other')
# Specific tags excluded
RL_EXCLUDED_TAGS = ('EX-301',)


def calc_rate(readings: list) -> float:
    if len(readings) < 2:
        return 0.0
    try:
        base = datetime.fromisoformat(readings[0]["reading_date"]).toordinal()
        days = np.array([
            datetime.fromisoformat(r["reading_date"]).toordinal() - base
            for r in readings
        ], dtype=float)
        mm = np.array([r["reading_mm"] for r in readings], dtype=float)
        m, _ = np.polyfit(days, mm, 1)
        return max(-m * 365.0, 0.0)
    except Exception:
        return 0.0


def calc_cml_rl(cml: dict, readings: list, cr_cache: Optional[float]) -> Optional[float]:
    if len(readings) < 2:
        return None
    t_min = cml.get("t_min") or (cml.get("nominal_thickness", 10) * 0.875)
    latest = readings[-1]["reading_mm"]
    remaining = latest - t_min
    if remaining <= 0:
        return 0.0
    rate = cr_cache if (cr_cache and cr_cache > 0) else calc_rate(readings)
    if rate <= 0:
        return 50.0
    return remaining / rate


def main():
    print("🔍 Fetching equipment...")
    eq_list = sb.table("equipment") \
        .select("id, tag, type, company_id") \
        .eq("is_active", True) \
        .execute()
    
    print(f"📋 Found {len(eq_list.data)} equipment to process\n")
    
    updated, skipped, errors = 0, 0, 0
    
    for i, eq in enumerate(eq_list.data):
        tag = eq["tag"]
        cid = eq["company_id"]
        eid = eq["id"]
        etype = eq["type"]
        
        # Skip non-eligible types
        if etype not in RL_ELIGIBLE_TYPES:
            # PSV: still create inspection_plan (NULL remaining_life_date)
            if etype == 'psv':
                existing = sb.table("inspection_plans") \
                    .select("id") \
                    .eq("equipment_id", eid).eq("company_id", cid).execute()
                if not existing.data:
                    sb.table("inspection_plans").insert({
                        "company_id": cid,
                        "equipment_id": eid,
                        "inspection_type": "external",
                        "remaining_life_date": None,
                    }).execute()
                    print(f"  [{i+1}/{len(eq_list.data)}] {tag:20s} → 📋 PSV plan created (NULL RL)")
                else:
                    print(f"  [{i+1}/{len(eq_list.data)}] {tag:20s} → 📋 PSV plan exists")
            else:
                skipped += 1
                print(f"  [{i+1}/{len(eq_list.data)}] {tag:20s} → ⏭️  type='{etype}' (not eligible)")
            continue
        
        # Skip specific excluded tags
        if tag in RL_EXCLUDED_TAGS:
            skipped += 1
            print(f"  [{i+1}/{len(eq_list.data)}] {tag:20s} → ⏭️  excluded by tag")
            continue
        
        # Get circuits
        circuits = sb.table("circuits") \
            .select("id, name, governing_cr_cache") \
            .eq("equipment_id", eid).eq("company_id", cid).execute()
        
        circuit_yl = []
        for circ in circuits.data:
            cmls = sb.table("cml_points") \
                .select("id, location_label, t_min, nominal_thickness") \
                .eq("circuit_id", circ["id"]).eq("company_id", cid).execute()
            
            for cml in cmls.data:
                readings = sb.table("thickness_readings") \
                    .select("reading_date, reading_mm") \
                    .eq("cml_point_id", cml["id"]).eq("company_id", cid) \
                    .order("reading_date").execute()
                
                rl = calc_cml_rl(cml, readings.data, circ.get("governing_cr_cache"))
                if rl is not None:
                    circuit_yl.append(rl)
                    # Write raw per-CML prediction to rl_predictions (uncapped)
                    existing_pred = sb.table("rl_predictions") \
                        .select("id") \
                        .eq("cml_point_id", cml["id"]).eq("company_id", cid).execute()
                    pred_data = {
                        "company_id": cid,
                        "cml_point_id": cml["id"],
                        "predicted_rl_years": round(rl, 2),
                        "confidence_low": None,
                        "confidence_high": None,
                    }
                    if existing_pred.data:
                        sb.table("rl_predictions").update({"predicted_rl_years": round(rl, 2)}) \
                            .eq("id", existing_pred.data[0]["id"]).execute()
                    else:
                        sb.table("rl_predictions").insert(pred_data).execute()
        
        if not circuit_yl:
            skipped += 1
            print(f"  [{i+1}/{len(eq_list.data)}] {tag:20s} → ⏭️  no data")
            continue
        
        eq_yl_raw = min(circuit_yl)
        # CAP 30 years for inspection_plan
        CAP_YEARS = 30
        eq_yl = min(eq_yl_raw, CAP_YEARS)
        rl_date = (date.today() + timedelta(days=int(eq_yl * 365))).isoformat()
        cap_flag = " [CAPPED]" if eq_yl_raw > CAP_YEARS else ""
        
        # Upsert
        existing = sb.table("inspection_plans") \
            .select("id, approval_status") \
            .eq("equipment_id", eid).eq("company_id", cid).execute()
        
        plan = {
            "company_id": cid,
            "equipment_id": eid,
            "inspection_type": "external",
            "remaining_life_date": rl_date,
        }
        
        flag = " [manual_review]" if etype == "other" else ""
        
        if existing.data:
            p = existing.data[0]
            if p["approval_status"] in ("pending", None, "revised"):
                sb.table("inspection_plans").update({"remaining_life_date": rl_date}).eq("id", p["id"]).execute()
                updated += 1
                print(f"  [{i+1}/{len(eq_list.data)}] {tag:20s} → ✅ updated (RL={eq_yl_raw:.1f}y → {eq_yl:.1f}y, due={rl_date}){flag}{cap_flag}")
            else:
                skipped += 1
                print(f"  [{i+1}/{len(eq_list.data)}] {tag:20s} → ⏭️  already approved")
        else:
            sb.table("inspection_plans").insert(plan).execute()
            updated += 1
            print(f"  [{i+1}/{len(eq_list.data)}] {tag:20s} → ✅ created (RL={eq_yl_raw:.1f}y → {eq_yl:.1f}y, due={rl_date}){flag}{cap_flag}")
    
    print(f"\n{'='*50}")
    print(f"📊 Summary")
    print(f"  ✅ Updated/Inserted: {updated}")
    print(f"  ⏭️  Skipped:         {skipped}")
    print(f"  ❌ Errors:           {errors}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()