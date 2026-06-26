"""
DM Screener API routes.
POST /api/dm-screener/match/{equipment_id} — auto matching for a registered equipment.
GET  /api/dm-screener/query               — manual form-based screening.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.core.database import get_db
from app.services.dm_validation import match_equipment, query_manual

router = APIRouter(prefix="/dm-screener", tags=["dm-screener"])


@router.post("/match/{equipment_id}")
async def api_match_equipment(equipment_id: str, company_id: str = Query(...)):
    """Match a registered equipment against DM KB.
    Returns active / possible / related DMs with confidence.
    """
    db = get_db()
    equipment = (
        db.table("equipment")
        .select("*")
        .eq("id", equipment_id)
        .eq("company_id", company_id)
        .single()
        .execute()
    )
    if not equipment.data:
        raise HTTPException(status_code=404, detail="Equipment not found")

    result = match_equipment(equipment.data)

    # Save predicted DMs to dm_validation_results
    db.table("dm_validation_results").insert({
        "company_id": company_id,
        "equipment_id": equipment_id,
        "predicted_dm_codes": [d["dm_code"] for d in result["active"]],
        "actual_finding_dm_codes": [],
        "match_score": None,
    }).execute()

    return result


@router.get("/query")
async def api_query_manual(
    material: str = Query(..., description="Equipment material (e.g. 'Carbon Steel')"),
    fluid_service: str = Query(..., description="Fluid service (e.g. 'Sour Hydrocarbon')"),
    temp_min: Optional[float] = Query(None, description="Min operating temp in C"),
    temp_max: Optional[float] = Query(None, description="Max operating temp in C"),
    has_pwht: Optional[bool] = Query(None, description="PWHT applied"),
):
    """Manual DM screening — no registered equipment needed.
    Provide material + fluid at minimum.
    """
    return query_manual(
        material=material,
        fluid_service=fluid_service,
        temp_min=temp_min,
        temp_max=temp_max,
        has_pwht=has_pwht,
    )
