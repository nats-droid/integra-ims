from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

from app.api.auth import verify_jwt

# Import RBI modules
import sys
sys.path.insert(0, '/root/integra/backend')
from codecalc.tmin_calculator import calculate_tmin_piping, calculate_tmin_vessel
from codecalc.corrosion_rate import calculate_corrosion_rate
from fms_audit import calculate_fms
from timeline_planning import RiskTimeline
from inspection_equivalence import (
    InspectionRecord, 
    InspectionEffectiveness, 
    InspectionType,
    calculate_equivalence_credit
)
from complete_rbi_simplified import CompleteRBICalculator

router = APIRouter()

# ============================================================================
# CONVERSION UTILITIES
# ============================================================================

def mm_to_inch(mm: float) -> float:
    return mm / 25.4

def inch_to_mm(inch: float) -> float:
    return inch * 25.4

def bar_to_psi(bar: float) -> float:
    return bar * 14.5038

def psi_to_bar(psi: float) -> float:
    return psi / 14.5038

def mpa_to_psi(mpa: float) -> float:
    return mpa * 145.038

def psi_to_mpa(psi: float) -> float:
    return psi / 145.038

def celsius_to_fahrenheit(c: float) -> float:
    return (c * 9/5) + 32

def fahrenheit_to_celsius(f: float) -> float:
    return (f - 32) * 5/9

def mm_yr_to_mpy(mm_yr: float) -> float:
    """mm/yr to mils per year"""
    return mm_yr / 0.0254

def mpy_to_mm_yr(mpy: float) -> float:
    """mils per year to mm/yr"""
    return mpy * 0.0254

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TminRequest(BaseModel):
    equipment_type: str = Field(..., pattern="^(pipe|vessel)$")
    pressure_bar: float = Field(..., gt=0)
    allowable_stress_mpa: float = Field(..., gt=0)
    joint_efficiency: float = Field(..., gt=0, le=1.0)
    corrosion_allowance_mm: float = Field(default=0.0, ge=0)
    design_temp_c: float
    # Pipe-specific
    od_mm: Optional[float] = Field(None, gt=0)
    nps_in: Optional[float] = Field(None, gt=0)
    # Vessel-specific
    id_mm: Optional[float] = Field(None, gt=0)

class CorrosionRateRequest(BaseModel):
    readings: List[Dict[str, str]] = Field(..., min_length=2)

class FMSRequest(BaseModel):
    leadership: float = Field(..., ge=0, le=100)
    process_safety_info: float = Field(..., ge=0, le=100)
    risk_management: float = Field(..., ge=0, le=100)
    operations: float = Field(..., ge=0, le=100)
    maintenance: float = Field(..., ge=0, le=100)
    inspection: float = Field(..., ge=0, le=100)

class TimelineRequest(BaseModel):
    pof_0: float = Field(..., ge=0)
    cof: float = Field(..., ge=0)
    corrosion_rate_mm_yr: float = Field(..., ge=0)
    t_actual_mm: float = Field(..., gt=0)
    t_required_mm: float = Field(..., gt=0)
    horizon_years: int = Field(default=10, ge=1, le=30)

class InspectionInput(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    effectiveness: str = Field(..., pattern="^[A-E]$")
    inspection_type: str

class EquivalenceRequest(BaseModel):
    inspections: List[InspectionInput] = Field(..., min_length=1)

class CompleteRBIRequest(BaseModel):
    component_id: str
    component_type: str
    fluid_type: str
    pressure_bar: float = Field(..., gt=0)
    temp_c: float
    diameter_mm: float = Field(..., gt=0)
    fms: float = Field(default=1.0, ge=0, le=10.0)
    damage_factors: Dict[str, float]

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/calculate-tmin")
async def calculate_tmin(
    req: TminRequest,
    user: dict = Depends(verify_jwt)
):
    """
    Calculate minimum required thickness per API 570/510/653
    Input: SI units (bar, MPa, mm, °C)
    Output: SI units (mm)
    """
    try:
        # Convert to imperial for calculation
        P_psi = bar_to_psi(req.pressure_bar)
        S_psi = mpa_to_psi(req.allowable_stress_mpa)
        E = req.joint_efficiency
        ca_inch = mm_to_inch(req.corrosion_allowance_mm)
        
        result = None
        
        if req.equipment_type == "pipe":
            if not req.od_mm or not req.nps_in:
                raise HTTPException(status_code=422, detail="pipe requires od_mm and nps_in")
            
            D_inch = mm_to_inch(req.od_mm)
            
            result = calculate_tmin_piping(
                P=P_psi,
                D=D_inch,
                S=S_psi,
                E=E,
                NPS=req.nps_in,
                T_design=req.design_temp_c,
                corrosion_allowance=ca_inch
            )
        
        elif req.equipment_type == "vessel":
            if not req.id_mm:
                raise HTTPException(status_code=422, detail="vessel requires id_mm")
            
            R_inch = mm_to_inch(req.id_mm) / 2
            
            result = calculate_tmin_vessel(
                P=P_psi,
                R_or_D=R_inch,
                S=S_psi,
                E=E,
                component_type='shell',
                corrosion_allowance=ca_inch
            )
        else:
            raise HTTPException(status_code=422, detail="equipment_type must be pipe or vessel")
        
        # Convert thickness values to mm
        result_mm = {}
        for key, value in result.items():
            if 't_' in key.lower() or 'thickness' in key.lower():
                if isinstance(value, (int, float)):
                    result_mm[key] = inch_to_mm(value)
                else:
                    result_mm[key] = value
            else:
                result_mm[key] = value
        
        return {"status": "ok", "data": result_mm}
    
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/calculate-corrosion-rate")
async def calculate_corrosion_rate_endpoint(
    req: CorrosionRateRequest,
    user: dict = Depends(verify_jwt)
):
    """
    Calculate corrosion rate from thickness readings
    Input: thickness in mm, dates as YYYY-MM-DD
    Output: corrosion rates in mm/yr
    """
    try:
        # Convert mm to inch for calculation
        thickness_history_inch = []
        for reading in req.readings:
            thickness_history_inch.append({
                'date': reading['date'],
                'thickness': mm_to_inch(float(reading['thickness_mm']))
            })
        
        result = calculate_corrosion_rate(thickness_history_inch)
        
        # Convert corrosion rates to mm/yr
        result_mm = {}
        for key, value in result.items():
            if 'CR' in key or 'rate' in key.lower():
                if isinstance(value, (int, float)):
                    result_mm[key] = mpy_to_mm_yr(value)
                else:
                    result_mm[key] = value
            else:
                result_mm[key] = value
        
        return {"status": "ok", "data": result_mm}
    
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/calculate-fms")
async def calculate_fms_endpoint(
    req: FMSRequest,
    user: dict = Depends(verify_jwt)
):
    """
    Calculate FMS (Facility Management Score) from 6 section scores
    Input: 6 scores (0-100)
    Output: FMS value
    """
    try:
        audit_scores = {
            'leadership': req.leadership,
            'process_safety_info': req.process_safety_info,
            'risk_management': req.risk_management,
            'operations': req.operations,
            'maintenance': req.maintenance,
            'inspection': req.inspection
        }
        
        result = calculate_fms(audit_scores)
        
        return {"status": "ok", "data": result}
    
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/calculate-timeline")
async def calculate_timeline_endpoint(
    req: TimelineRequest,
    user: dict = Depends(verify_jwt)
):
    """
    Calculate 10-year risk trajectory
    Input: SI units (mm, mm/yr)
    Output: risk timeline
    """
    try:
        # Convert to imperial for calculation
        cr_mpy = mm_yr_to_mpy(req.corrosion_rate_mm_yr)
        t_actual_inch = mm_to_inch(req.t_actual_mm)
        t_required_inch = mm_to_inch(req.t_required_mm)
        
        timeline = RiskTimeline(
            assessment_date=datetime.now(),
            plan_horizon_years=req.horizon_years
        )
        
        trajectory = timeline.calculate_risk_trajectory(
            pof_0=req.pof_0,
            cof=req.cof,
            corrosion_rate_mpy=cr_mpy,
            t_actual=t_actual_inch,
            t_required=t_required_inch
        )
        
        return {"status": "ok", "data": trajectory}
    
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/calculate-equivalence")
async def calculate_equivalence_endpoint(
    req: EquivalenceRequest,
    user: dict = Depends(verify_jwt)
):
    """
    Calculate inspection equivalence credit (2B = 1A)
    Input: inspection history
    Output: equivalence credit
    """
    try:
        inspection_records = []
        
        for insp in req.inspections:
            try:
                effectiveness = InspectionEffectiveness(insp.effectiveness)
            except ValueError:
                raise HTTPException(
                    status_code=422, 
                    detail=f"Invalid effectiveness: {insp.effectiveness}. Must be A, B, C, D, or E"
                )
            
            try:
                insp_type = InspectionType(insp.inspection_type)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid inspection_type: {insp.inspection_type}"
                )
            
            record = InspectionRecord(
                inspection_date=datetime.strptime(insp.date, '%Y-%m-%d'),
                effectiveness=effectiveness,
                inspection_type=insp_type
            )
            inspection_records.append(record)
        
        result = calculate_equivalence_credit(inspection_records)
        
        return {"status": "ok", "data": result}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/complete-rbi")
async def complete_rbi_endpoint(
    req: CompleteRBIRequest,
    user: dict = Depends(verify_jwt)
):
    """
    Complete RBI calculation with all damage mechanisms
    Input: SI units (bar, °C, mm)
    Output: RBI result with risk matrix
    """
    try:
        # Convert to imperial for calculation
        component_data = {
            'component_id': req.component_id,
            'component_type': req.component_type,
            'fluid_type': req.fluid_type,
            'operating_pressure_psig': bar_to_psi(req.pressure_bar) - 14.7,  # gauge pressure
            'operating_temp_f': celsius_to_fahrenheit(req.temp_c),
            'diameter_inches': mm_to_inch(req.diameter_mm),
            'fms': req.fms
        }
        
        calculator = CompleteRBICalculator()
        result = calculator.calculate_complete_rbi(component_data, req.damage_factors)
        
        return {"status": "ok", "data": result}
    
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint (no auth required)
    """
    return {
        "status": "ok",
        "service": "RBI API",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/v1/rbi/calculate-tmin",
            "POST /api/v1/rbi/calculate-corrosion-rate",
            "POST /api/v1/rbi/calculate-fms",
            "POST /api/v1/rbi/calculate-timeline",
            "POST /api/v1/rbi/calculate-equivalence",
            "POST /api/v1/rbi/complete-rbi",
            "GET /api/v1/rbi/health"
        ]
    }
