"""Remaining Life API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.services.remaining_life import batch_recalculate, calculate_for_equipment
from supabase import Client

router = APIRouter(prefix="/api/v1/remaining-life", tags=["Remaining Life"])


class CalculateRequest(BaseModel):
    equipment_ids: Optional[list[str]] = None
    company_id: Optional[str] = None


@router.post("/calculate")
async def calculate(req: CalculateRequest, db: Client = Depends(get_db)):
    """Batch calculate remaining life for all (or specified) equipment.
    Uses company_id from JWT or request body."""
    if not req.company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    
    result = await batch_recalculate(
        db=db,
        company_id=req.company_id,
        equipment_ids=req.equipment_ids,
    )
    return result


@router.get("/preview/{equipment_id}")
async def preview(equipment_id: str, company_id: str, db: Client = Depends(get_db)):
    """Preview remaining life calculation for a single equipment without saving."""
    result = calculate_for_equipment(db, equipment_id, company_id)
    return result
