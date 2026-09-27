"""
RBI (Risk-Based Inspection) API Router
Integrates complete RBI API 581 4th Edition calculator
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/v1/rbi", tags=["RBI"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TminRequest(BaseModel):
    """Required thickness calculation request"""
    design_code: str  # B31.3, ASME_VIII_1, API_653, API_574
    equipment_type: str  # pipe, vessel, tank
    pressure: float  # bar or psig
    diameter: float  # mm or inches
    design_temp: float  # °C or °F
    material: str
    corrosion_allowance: float
    joint_efficiency: Optional[float] = 1.0
    unit_system: Optional[str] = "SI"  # SI or USC


class CorrosionRateRequest(BaseModel):
    """Corrosion rate calculation request"""
    thickness_history: List[Dict[str, Any]]  # [{"date": "2020-01-01", "thickness": 20.0}, ...]
    tmin: float
    design_life: Optional[float] = 20.0


class FMSRequest(BaseModel):
    """FMS Audit request"""
    audit_scores: Dict[str, int]  # 14 categories


class TimelineRequest(BaseModel):
    """Risk timeline planning request"""
    equipment_id: str
    initial_pof: float
    cof: float
    corrosion_rate: float
    current_thickness: float
    years: Optional[int] = 10


class EquivalenceRequest(BaseModel):
    """Inspection equivalence request"""
    inspections: List[Dict[str, Any]]  # [{"type": "A", "date": "2020-01-01", "effectiveness": 0.9}, ...]
    damage_mechanism: str


class CompleteRBIRequest(BaseModel):
    """Complete RBI assessment request"""
    equipment_id: str
    equipment_type: str
    damage_mechanism: str
    operating_pressure: float
    operating_temp: float
    diameter: float
    thickness_current: float
    thickness_history: Optional[List[Dict[str, Any]]] = None
    material: str
    fms_audit_scores: Optional[Dict[str, int]] = None
    inspection_history: Optional[List[Dict[str, Any]]] = None
    consequence_data: Optional[Dict[str, Any]] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/calculate-tmin")
async def calculate_tmin(request: TminRequest):
    """
    Calculate required minimum thickness per code (API 570/510/653, B31.3, ASME VIII)
    
    Returns:
    - t_required: Required thickness by formula
    - t_min: Required thickness + corrosion allowance
    - code: Applied code/standard
    - steps: Calculation steps for audit trail
    """
    try:
        # Import RBI calculator modules
        from codecalc.tmin_calculator import calculate_tmin_piping, calculate_tmin_vessel
        
        # Route to appropriate calculator
        if request.equipment_type == "pipe":
            # For piping: calculate_tmin_piping(P, D, S, E, NPS, T_design, W, Y, corrosion_allowance)
            result = calculate_tmin_piping(
                P=request.pressure,
                D=request.diameter,
                S=20000,  # Allowable stress (default for carbon steel)
                E=request.joint_efficiency,
                NPS=request.diameter,
                T_design=request.design_temp,
                corrosion_allowance=request.corrosion_allowance,
            )
        elif request.equipment_type in ["vessel", "tank"]:
            # For vessel: calculate_tmin_vessel(P, R_or_D, S, E, component_type, corrosion_allowance)
            result = calculate_tmin_vessel(
                P=request.pressure,
                R_or_D=request.diameter/2,  # Radius
                S=20000,  # Allowable stress
                E=request.joint_efficiency,
                component_type='shell',
                corrosion_allowance=request.corrosion_allowance,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported equipment type: {request.equipment_type}")
        
        return {
            "success": True,
            "data": result,
            "equipment_id": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-corrosion-rate")
async def calculate_corrosion_rate(request: CorrosionRateRequest):
    """
    Calculate corrosion rate and remaining life from thickness history
    
    Returns:
    - LT_rate: Long-term corrosion rate (mm/yr)
    - ST_rate: Short-term corrosion rate (mm/yr)
    - remaining_life: Years until t_min reached
    - trend: Accelerating, stable, or decelerating
    """
    try:
        from codecalc.corrosion_rate import calculate_corrosion_rate
        
        # Convert thickness history to proper format
        thickness_history = [
            (datetime.fromisoformat(item["date"]), item["thickness"])
            for item in request.thickness_history
        ]
        
        result = calculate_corrosion_rate(
            thickness_history=thickness_history,
            tmin=request.tmin,
            design_life=request.design_life,
        )
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-fms")
async def calculate_fms(request: FMSRequest):
    """
    Calculate FMS (Management Systems Factor) from 72-item audit
    
    Returns:
    - pscore: Total audit score (0-100)
    - fms: FMS factor (0.5 - 2.5)
    - interpretation: Management system quality level
    """
    try:
        from fms_audit import calculate_fms
        
        result = calculate_fms(request.audit_scores)
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-timeline")
async def calculate_timeline(request: TimelineRequest):
    """
    Calculate 10-year risk timeline with 0.5-year time steps
    
    Returns:
    - timeline: List of {year, pof, risk, thickness} points
    - recommended_inspection_dates: Optimal inspection schedule
    - risk_trajectory: Increasing, stable, or decreasing
    """
    try:
        from timeline_planning import calculate_risk_timeline
        
        result = calculate_risk_timeline(
            equipment_id=request.equipment_id,
            initial_pof=request.initial_pof,
            cof=request.cof,
            corrosion_rate_mpy=request.corrosion_rate,
            current_thickness_inches=request.current_thickness,
            years=request.years,
        )
        
        return {
            "success": True,
            "data": result,
            "equipment_id": request.equipment_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-equivalence")
async def calculate_equivalence(request: EquivalenceRequest):
    """
    Calculate inspection equivalence credit (2 Type B = 1 Type A)
    
    Returns:
    - total_credit: Equivalent Type A inspections
    - meets_requirement: True if sufficient credit
    - recommendation: Next inspection type needed
    """
    try:
        from inspection_equivalence import calculate_inspection_credit
        
        result = calculate_inspection_credit(
            inspections=request.inspections,
            damage_mechanism=request.damage_mechanism,
        )
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete-rbi")
async def complete_rbi(request: CompleteRBIRequest):
    """
    Complete RBI assessment - integrates all modules
    
    Returns:
    - pof: Probability of failure
    - cof: Consequence of failure
    - risk: Risk score (POF × COF)
    - risk_category: High/Medium-High/Medium/Medium-Low/Low
    - next_inspection_date: Recommended date
    - timeline: 10-year risk trajectory
    - flags: Data quality flags (MISSING, ASSUMED, etc.)
    - steps: Complete calculation audit trail
    """
    try:
        from complete_rbi_simplified import calculate_complete_rbi
        
        result = calculate_complete_rbi(
            equipment_id=request.equipment_id,
            equipment_type=request.equipment_type,
            damage_mechanism=request.damage_mechanism,
            operating_pressure=request.operating_pressure,
            operating_temp=request.operating_temp,
            diameter=request.diameter,
            thickness_current=request.thickness_current,
            thickness_history=request.thickness_history,
            material=request.material,
            fms_audit_scores=request.fms_audit_scores,
            inspection_history=request.inspection_history,
            consequence_data=request.consequence_data,
        )
        
        return {
            "success": True,
            "data": result,
            "equipment_id": request.equipment_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def rbi_health():
    """RBI module health check"""
    try:
        from codecalc.tmin_calculator import calculate_tmin_piping
        
        return {
            "status": "ok",
            "module": "RBI API 581",
            "version": "1.0.0",
            "features": [
                "Code calculations (API 570/510/653)",
                "FMS audit (72-item)",
                "Risk timeline (10-year)",
                "Inspection equivalence (2B=1A)",
                "Complete RBI assessment",
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
