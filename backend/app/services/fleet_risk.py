"""
Fleet-wide Risk Heatmap (PRD Section 5.3)
Combines:
1. Physical condition: proportion of equipment/CML near t_min or short RL
2. Material vulnerability: DM Screener active DM count per area
"""
from app.core.database import get_db


async def compute(company_id: str, area_id: str = None) -> dict:
    """Compute fleet-wide risk aggregation per area."""
    db = get_db()
    
    # Build query for areas
    query = db.table("plant_areas") \
        .select("id, name") \
        .eq("company_id", company_id)
    
    if area_id:
        query = query.eq("id", area_id)
    
    areas = query.execute()
    
    area_risks = []
    for area in areas.data:
        # Get equipment in this area
        equip = db.table("equipment") \
            .select("id, tag, risk_category") \
            .eq("company_id", company_id) \
            .eq("area_id", area["id"]) \
            .execute()
        
        total_equip = len(equip.data)
        if total_equip == 0:
            continue
        
        high_risk = sum(1 for e in equip.data if e.get("risk_category") in ("high", "critical"))
        non_compliant = sum(1 for e in equip.data if e.get("compliance_status") == "non-compliant")
        
        # Risk score: combination of high-risk proportion + non-compliant
        risk_score = (high_risk / total_equip * 0.6 + non_compliant / total_equip * 0.4) * 100
        
        # Risk level
        if risk_score >= 50:
            risk_level = "critical"
        elif risk_score >= 30:
            risk_level = "high"
        elif risk_score >= 15:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        area_risks.append({
            "area_id": area["id"],
            "area_name": area["name"],
            "total_equipment": total_equip,
            "high_risk_count": high_risk,
            "non_compliant_count": non_compliant,
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
        })
    
    # Save snapshot
    db.table("fleet_risk_snapshots").insert({
        "company_id": company_id,
        "area_id": area_id,
        "risk_summary": {
            "areas": area_risks,
            "total_areas": len(area_risks),
        },
    }).execute()
    
    return {
        "company_id": company_id,
        "areas": area_risks,
        "total_areas": len(area_risks),
        "highest_risk": max(area_risks, key=lambda a: a["risk_score"]) if area_risks else None,
    }
